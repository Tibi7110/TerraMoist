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

export default function App() {
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

  if (authState.status !== "authenticated") {
    return (
      <AuthScreen
        pending={authPending || authState.status === "loading"}
        error={authError}
        onAuthenticate={handleAuthenticate}
      />
    );
  }

  return (
    <FarmWorkspace
      currentUser={authState.user}
      onLogout={handleLogout}
    />
  );
}
