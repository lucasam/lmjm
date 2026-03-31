import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock localStorage
const store: Record<string, string> = {};
const localStorageMock = {
  getItem: vi.fn((key: string) => store[key] ?? null),
  setItem: vi.fn((key: string, value: string) => { store[key] = value; }),
  removeItem: vi.fn((key: string) => { delete store[key]; }),
  clear: vi.fn(() => { Object.keys(store).forEach(k => delete store[k]); }),
};
Object.defineProperty(globalThis, 'localStorage', { value: localStorageMock, writable: true });

// Mock window.location
const locationMock = { href: '' };
Object.defineProperty(globalThis.window, 'location', { value: locationMock, writable: true });

// Mock global fetch
const fetchMock = vi.fn();
vi.stubGlobal('fetch', fetchMock);

function makeResponse(status: number, body: unknown): Response {
  const ok = status >= 200 && status < 300;
  return {
    ok,
    status,
    statusText: ok ? 'OK' : status === 401 ? 'Unauthorized' : 'Error',
    json: () => Promise.resolve(body),
    headers: new Headers(),
    redirected: false,
    type: 'basic' as ResponseType,
    url: '',
    clone: function () { return makeResponse(status, body); },
    body: null,
    bodyUsed: false,
    arrayBuffer: () => Promise.resolve(new ArrayBuffer(0)),
    blob: () => Promise.resolve(new Blob()),
    formData: () => Promise.resolve(new FormData()),
    text: () => Promise.resolve(JSON.stringify(body)),
    bytes: () => Promise.resolve(new Uint8Array()),
  } as Response;
}

let listCattleAnimals: () => Promise<unknown>;

beforeEach(async () => {
  vi.resetModules();
  fetchMock.mockReset();
  localStorageMock.clear();
  localStorageMock.getItem.mockImplementation((key: string) => store[key] ?? null);
  localStorageMock.setItem.mockImplementation((key: string, value: string) => { store[key] = value; });
  localStorageMock.removeItem.mockImplementation((key: string) => { delete store[key]; });
  locationMock.href = '';

  const client = await import('../client');
  listCattleAnimals = client.listCattleAnimals;
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('API Client', () => {
  describe('Bearer token attachment (Req 9.12)', () => {
    it('attaches Bearer token from localStorage to requests', async () => {
      store['lmjm_access_token'] = 'my-jwt-token';
      fetchMock.mockResolvedValueOnce(makeResponse(200, []));

      await listCattleAnimals();

      expect(fetchMock).toHaveBeenCalledTimes(1);
      const callArgs = fetchMock.mock.calls[0];
      expect(callArgs[1].headers['Authorization']).toBe('Bearer my-jwt-token');
    });

    it('sends request without Authorization header when no token stored', async () => {
      fetchMock.mockResolvedValueOnce(makeResponse(200, []));

      await listCattleAnimals();

      expect(fetchMock).toHaveBeenCalledTimes(1);
      const callArgs = fetchMock.mock.calls[0];
      expect(callArgs[1].headers['Authorization']).toBeUndefined();
    });
  });

  describe('401 refresh + retry logic (Req 9.13)', () => {
    it('refreshes token and retries on 401', async () => {
      store['lmjm_access_token'] = 'expired-token';
      store['lmjm_refresh_token'] = 'my-refresh-token';

      // First call: 401
      fetchMock.mockResolvedValueOnce(makeResponse(401, {}));
      // Refresh token call: success
      fetchMock.mockResolvedValueOnce(
        makeResponse(200, { access_token: 'new-token', id_token: 'new-id-token' })
      );
      // Retry: success
      fetchMock.mockResolvedValueOnce(makeResponse(200, [{ pk: '1', ear_tag: 'A001' }]));

      const result = await listCattleAnimals();

      expect(fetchMock).toHaveBeenCalledTimes(3);

      // Verify refresh call
      const [refreshUrl, refreshOptions] = fetchMock.mock.calls[1];
      expect(refreshUrl).toContain('/oauth2/token');
      expect(refreshOptions.method).toBe('POST');

      // Verify retry used new token
      const [, retryOptions] = fetchMock.mock.calls[2];
      expect(retryOptions.headers['Authorization']).toBe('Bearer new-token');

      // Verify new token stored
      expect(store['lmjm_access_token']).toBe('new-token');

      expect(result).toEqual([{ pk: '1', ear_tag: 'A001' }]);
    });

    it('clears tokens and redirects to /login when refresh fails (Req 9.14)', async () => {
      store['lmjm_access_token'] = 'expired-token';
      store['lmjm_refresh_token'] = 'bad-refresh-token';

      fetchMock.mockResolvedValueOnce(makeResponse(401, {}));
      fetchMock.mockResolvedValueOnce(makeResponse(400, { error: 'invalid_grant' }));

      await expect(listCattleAnimals()).rejects.toThrow('Session expired');

      expect(localStorageMock.removeItem).toHaveBeenCalledWith('lmjm_access_token');
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('lmjm_id_token');
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('lmjm_refresh_token');
      expect(locationMock.href).toBe('/login');
    });

    it('clears tokens when no refresh token is available', async () => {
      store['lmjm_access_token'] = 'expired-token';

      fetchMock.mockResolvedValueOnce(makeResponse(401, {}));

      await expect(listCattleAnimals()).rejects.toThrow('Session expired');
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('lmjm_access_token');
      expect(locationMock.href).toBe('/login');
    });
  });

  describe('Error throwing on non-2xx (Req 9.9)', () => {
    it('throws error with status code and message from response body', async () => {
      store['lmjm_access_token'] = 'valid-token';
      fetchMock.mockResolvedValueOnce(makeResponse(404, { message: 'Animal not found' }));

      try {
        await listCattleAnimals();
        expect.fail('Should have thrown');
      } catch (err: unknown) {
        const error = err as { statusCode: number; message: string; name: string };
        expect(error.name).toBe('ApiError');
        expect(error.statusCode).toBe(404);
        expect(error.message).toBe('Animal not found');
      }
    });

    it('uses statusText when response body has no message field', async () => {
      store['lmjm_access_token'] = 'valid-token';
      const resp = makeResponse(500, {});
      resp.json = () => Promise.reject(new Error('no json'));
      Object.defineProperty(resp, 'statusText', { value: 'Internal Server Error', writable: true });
      fetchMock.mockResolvedValueOnce(resp);

      try {
        await listCattleAnimals();
        expect.fail('Should have thrown');
      } catch (err: unknown) {
        const error = err as { statusCode: number; message: string };
        expect(error.statusCode).toBe(500);
        expect(error.message).toBe('Internal Server Error');
      }
    });
  });
});
