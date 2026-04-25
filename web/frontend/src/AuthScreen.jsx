import { useState } from "react";

const INITIAL_FORM = {
  name: "",
  email: "",
  password: "",
};

export default function AuthScreen({ pending, error, onAuthenticate }) {
  const [mode, setMode] = useState("register");
  const [form, setForm] = useState(INITIAL_FORM);

  function updateField(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    await onAuthenticate(mode, form);
  }

  function switchMode(nextMode) {
    setMode(nextMode);
    setForm((current) => ({
      ...current,
      password: "",
    }));
  }

  const isRegister = mode === "register";

  return (
    <div className="auth-shell">
      <section className="auth-hero">
        <div className="auth-hero__badge">TerraMoist Platform</div>
        <h1>Build your farm workspace.</h1>

      </section>

      <section className="auth-panel">
        <div className="auth-panel__switch">
          <button
            type="button"
            className={mode === "register" ? "active" : ""}
            onClick={() => switchMode("register")}
          >
            Create account
          </button>
          <button
            type="button"
            className={mode === "login" ? "active" : ""}
            onClick={() => switchMode("login")}
          >
            Sign in
          </button>
        </div>

        <header className="auth-panel__header">
          <h2>{isRegister ? "Welcome to TerraMoist" : "Welcome back"}</h2>
          <p>
            {isRegister
              ? "Create your farmer account to save land and irrigation data."
              : "Sign in to continue working on your farm map."}
          </p>
        </header>

        <form className="auth-form" onSubmit={handleSubmit}>
          {isRegister && (
            <label className="auth-field">
              <span>Name</span>
              <input
                name="name"
                type="text"
                autoComplete="name"
                value={form.name}
                onChange={updateField}
                placeholder="Alex Popescu"
                required
              />
            </label>
          )}

          <label className="auth-field">
            <span>Email</span>
            <input
              name="email"
              type="email"
              autoComplete="email"
              value={form.email}
              onChange={updateField}
              placeholder="alex@farm.ro"
              required
            />
          </label>

          <label className="auth-field">
            <span>Password</span>
            <input
              name="password"
              type="password"
              autoComplete={isRegister ? "new-password" : "current-password"}
              value={form.password}
              onChange={updateField}
              placeholder="Minimum 8 characters"
              minLength={8}
              required
            />
          </label>

          {error && <p className="auth-error">{error}</p>}

          <button type="submit" className="auth-submit" disabled={pending}>
            {pending ? "Working..." : isRegister ? "Create account" : "Sign in"}
          </button>
        </form>
      </section>
    </div>
  );
}
