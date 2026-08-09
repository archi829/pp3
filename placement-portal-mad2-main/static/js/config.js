/**
 * config.js — fetch-based API wrapper, JWT helpers, and auth utilities.
 * Exposes window.api (get/post/put/delete) and window.auth.
 * Must load before any component/router script that uses window.api / window.auth.
 */
(function () {
  var BASE_URL = '/api';

  // ---------------------------------------------------------------------------
  // Toast helper
  // ---------------------------------------------------------------------------
  // Minimal Bootstrap 5 toast helper for surfacing errors that aren't tied to a
  // specific component's inline <error-alert> (e.g. 403s on background actions).
  // Lazily creates a single top-right toast container and reuses it.
  function showToast(message) {
    var container = document.getElementById('pp-toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'pp-toast-container';
      container.className = 'toast-container position-fixed top-0 end-0 p-3';
      container.style.zIndex = 1080;
      document.body.appendChild(container);
    }

    var toastEl = document.createElement('div');
    toastEl.className = 'toast align-items-center text-bg-danger border-0';
    toastEl.setAttribute('role', 'alert');
    toastEl.innerHTML =
      '<div class="d-flex">' +
      '  <div class="toast-body"></div>' +
      '  <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>' +
      '</div>';
    // textContent, not innerHTML, for the message itself — avoids injecting
    // unescaped server text into the DOM.
    toastEl.querySelector('.toast-body').textContent = message;

    container.appendChild(toastEl);
    var toast = new bootstrap.Toast(toastEl, { delay: 5000 });
    toast.show();
    toastEl.addEventListener('hidden.bs.toast', function () {
      toastEl.remove();
    });
  }
  window.showToast = showToast;

  // ---------------------------------------------------------------------------
  // Core fetch wrapper
  // ---------------------------------------------------------------------------
  /**
   * request(method, path, options)
   *
   * options:
   *   params       — plain object serialised as ?key=value query string
   *   data         — request body; if FormData sent as-is, otherwise JSON-encoded
   *   headers      — extra / override headers (pass { 'Content-Type': undefined }
   *                  to let the browser set the multipart boundary for FormData)
   *   responseType — 'blob' to resolve with a Blob instead of parsed JSON
   *
   * Returns a Promise that resolves to { data, headers } (mirrors the axios
   * response shape used throughout the component files) or rejects with an
   * Error that has a .response = { status, data } property.
   */
  function request(method, path, options) {
    options = options || {};

    // Build URL with optional query params
    var url = BASE_URL + path;
    if (options.params && Object.keys(options.params).length) {
      var qs = Object.keys(options.params)
        .filter(function (k) {
          return options.params[k] !== undefined && options.params[k] !== null;
        })
        .map(function (k) {
          return encodeURIComponent(k) + '=' + encodeURIComponent(options.params[k]);
        })
        .join('&');
      if (qs) url += '?' + qs;
    }

    // Build headers
    var headers = {};

    // Attach JWT if available
    var token = window.auth && window.auth.getToken();
    if (token) {
      headers['Authorization'] = 'Bearer ' + token;
    }

    // Determine body and Content-Type
    var body;
    var isFormData = options.data instanceof FormData;
    if (options.data !== undefined && options.data !== null) {
      if (isFormData) {
        // Let the browser set the correct multipart/form-data boundary automatically —
        // do NOT set Content-Type manually.
        body = options.data;
      } else {
        headers['Content-Type'] = 'application/json';
        body = JSON.stringify(options.data);
      }
    }

    // Apply caller-supplied header overrides.
    // A value of `undefined` means "remove this header" (e.g. Content-Type for FormData).
    if (options.headers) {
      Object.keys(options.headers).forEach(function (k) {
        if (options.headers[k] === undefined) {
          delete headers[k];
        } else {
          headers[k] = options.headers[k];
        }
      });
    }

    return fetch(url, {
      method: method.toUpperCase(),
      headers: headers,
      body: body
    }).then(function (response) {
      // Handle 401 — clear session, bounce to /login
      if (response.status === 401) {
        window.auth.logout();
        if (window.location.pathname !== '/login') {
          if (window.router) {
            window.router.push('/login').catch(function () {});
          } else {
            window.location.href = '/login';
          }
        }
        // Still reject so component .catch() handlers run
        var err401 = new Error('Unauthorised');
        err401.response = { status: 401, data: {} };
        return Promise.reject(err401);
      }

      // Blob responses (e.g. resume / offer-letter downloads)
      if (options.responseType === 'blob') {
        if (!response.ok) {
          return response.json().catch(function () { return {}; }).then(function (errData) {
            var err = new Error('Request failed');
            err.response = { status: response.status, data: errData };
            if (response.status === 403) {
              var msg403 = (errData && errData.msg) || 'You do not have access to perform this action.';
              if (typeof window.showToast === 'function') window.showToast(msg403);
            }
            return Promise.reject(err);
          });
        }
        return response.blob().then(function (blob) {
          var headersMap = {};
          response.headers.forEach(function (value, key) {
            headersMap[key.toLowerCase()] = value;
          });
          return { data: blob, headers: headersMap };
        });
      }

      // Normal JSON responses
      return response.json().catch(function () { return {}; }).then(function (json) {
        if (!response.ok) {
          var err = new Error('Request failed');
          err.response = { status: response.status, data: json };
          if (response.status === 403) {
            var msg403 = (json && json.msg) || 'You do not have access to perform this action.';
            if (typeof window.showToast === 'function') window.showToast(msg403);
          }
          return Promise.reject(err);
        }
        return { data: json, headers: {} };
      });
    });
  }

  // ---------------------------------------------------------------------------
  // Public API surface (mirrors the axios instance used in components)
  // ---------------------------------------------------------------------------
  window.api = {
    get: function (path, options) {
      return request('GET', path, options);
    },
    post: function (path, data, options) {
      return request('POST', path, Object.assign({}, options || {}, { data: data }));
    },
    put: function (path, data, options) {
      return request('PUT', path, Object.assign({}, options || {}, { data: data }));
    },
    delete: function (path, options) {
      return request('DELETE', path, options);
    }
  };

  // ---------------------------------------------------------------------------
  // Auth helpers
  // ---------------------------------------------------------------------------
  window.auth = {
    getToken: function () {
      return localStorage.getItem('token');
    },
    getRole: function () {
      return localStorage.getItem('role');
    },
    getUser: function () {
      return {
        id: localStorage.getItem('user_id'),
        email: localStorage.getItem('email'),
        role: localStorage.getItem('role')
      };
    },
    isAuthenticated: function () {
      return !!localStorage.getItem('token');
    },
    // data = { access_token, role, user_id, email } (the /api/auth/login response body)
    login: function (data) {
      localStorage.setItem('token', data.access_token);
      localStorage.setItem('role', data.role);
      localStorage.setItem('user_id', data.user_id);
      localStorage.setItem('email', data.email);
    },
    logout: function () {
      localStorage.removeItem('token');
      localStorage.removeItem('role');
      localStorage.removeItem('user_id');
      localStorage.removeItem('email');
    }
  };
})();
