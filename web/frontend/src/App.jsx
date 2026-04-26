import { useEffect, useState } from "react";
import AuthScreen from "./AuthScreen";
import FarmWorkspace from "./FarmWorkspace";
import {
  clearSession,
  fetchCurrentUser,
  loadStoredToken,
  loginUser,
  persistSession,
  registerUser,
} from "./auth";
import "./App.css";

const THEME_STORAGE_KEY = "terramoist.theme";

function loadTheme() {
  return window.localStorage.getItem(THEME_STORAGE_KEY) === "dark"
    ? "dark"
    : "white";
}

export default function App() {
  const [theme, setTheme] = useState(loadTheme);
  const [authState, setAuthState] = useState(() => {
    const token = loadStoredToken();
    return token
      ? { status: "loading", token, user: null }
      : { status: "anonymous", token: "", user: null };
  });
  const [authPending, setAuthPending] = useState(false);
  const [authError, setAuthError] = useState("");

  useEffect(() => {
    if (authState.status !== "loading" || !authState.token) {
      return;
    }

    let cancelled = false;

    fetchCurrentUser(authState.token)
      .then((session) => {
        if (cancelled) {
          return;
        }

        persistSession(session.token);
        setAuthState({
          status: "authenticated",
          token: session.token,
          user: session.user,
        });
      })
      .catch(() => {
        if (cancelled) {
          return;
        }

        clearSession();
        setAuthState({ status: "anonymous", token: "", user: null });
      });

    return () => {
      cancelled = true;
    };
  }, [authState.status, authState.token]);

  async function handleAuthenticate(mode, form) {
    setAuthPending(true);
    setAuthError("");

    try {
      const session =
        mode === "register"
          ? await registerUser(form)
          : await loginUser({
              email: form.email,
              password: form.password,
            });

      persistSession(session.token);
      setAuthState({
        status: "authenticated",
        token: session.token,
        user: session.user,
      });
    } catch (error) {
      setAuthError(error.message);
    } finally {
      setAuthPending(false);
    }
  }

  function handleLogout() {
    clearSession();
    setAuthError("");
    setAuthState({ status: "anonymous", token: "", user: null });
  }

  function handleThemeToggle() {
    setTheme((current) => {
      const next = current === "dark" ? "white" : "dark";
      window.localStorage.setItem(THEME_STORAGE_KEY, next);
      return next;
    });
  }

  if (authState.status !== "authenticated") {
    return (
      <AuthScreen
        theme={theme}
        onThemeToggle={handleThemeToggle}
        pending={authPending || authState.status === "loading"}
        error={authError}
        onAuthenticate={handleAuthenticate}
      />
    );
  }

  return (
    <FarmWorkspace
      theme={theme}
      onThemeToggle={handleThemeToggle}
      currentUser={authState.user}
      onLogout={handleLogout}
    />
  );
}
