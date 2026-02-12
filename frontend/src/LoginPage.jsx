/**
 * Watchtower AI - Login / Register Page
 * Dark themed auth form matching the app's design language.
 */

import { useState } from "react";
import { useAuth } from "./AuthContext";

export default function LoginPage() {
  const { login, register, error } = useAuth();
  const [mode, setMode] = useState("login"); // "login" | "register"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);
  const [localError, setLocalError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLocalError("");
    setLoading(true);

    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        if (password.length < 8) {
          setLocalError("Password must be at least 8 characters");
          setLoading(false);
          return;
        }
        await register(email, password, name);
      }
    } catch (err) {
      setLocalError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const displayError = localError || error;

  return (
    <div
      className="h-screen w-screen bg-[#0b0d14] flex items-center justify-center"
      style={{ fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif" }}
    >
      <div className="w-full max-w-sm px-6">
        {/* Logo / Title */}
        <div className="text-center mb-8">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-violet-500/30 to-violet-600/10 border border-violet-500/20 flex items-center justify-center mx-auto mb-4">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-violet-300">
              <rect x="2" y="3" width="20" height="14" rx="2" /><line x1="8" y1="21" x2="16" y2="21" /><line x1="12" y1="17" x2="12" y2="21" />
            </svg>
          </div>
          <h1 className="text-xl font-bold text-white/90 tracking-tight">Watchtower AI</h1>
          <p className="text-[13px] text-white/30 mt-1">
            {mode === "login" ? "Sign in to your account" : "Create a new account"}
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-3">
          {mode === "register" && (
            <div>
              <label className="block text-[11px] text-white/40 font-medium mb-1 uppercase tracking-wider">Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Your name (optional)"
                className="w-full bg-white/[0.04] border border-white/[0.08] rounded-xl px-4 py-2.5 text-[13px] text-white/85 placeholder-white/15 outline-none focus:border-violet-500/40 transition-colors"
              />
            </div>
          )}

          <div>
            <label className="block text-[11px] text-white/40 font-medium mb-1 uppercase tracking-wider">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
              autoComplete="email"
              className="w-full bg-white/[0.04] border border-white/[0.08] rounded-xl px-4 py-2.5 text-[13px] text-white/85 placeholder-white/15 outline-none focus:border-violet-500/40 transition-colors"
            />
          </div>

          <div>
            <label className="block text-[11px] text-white/40 font-medium mb-1 uppercase tracking-wider">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={mode === "register" ? "Minimum 8 characters" : "Your password"}
              required
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              className="w-full bg-white/[0.04] border border-white/[0.08] rounded-xl px-4 py-2.5 text-[13px] text-white/85 placeholder-white/15 outline-none focus:border-violet-500/40 transition-colors"
            />
          </div>

          {displayError && (
            <div className="text-[12px] text-red-400 bg-red-500/10 border border-red-500/15 rounded-xl px-4 py-2.5">
              {displayError}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-violet-600 hover:bg-violet-500 text-white font-semibold text-[13px] rounded-xl py-2.5 transition-colors disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer mt-2"
          >
            {loading
              ? mode === "login" ? "Signing in..." : "Creating account..."
              : mode === "login" ? "Sign In" : "Create Account"
            }
          </button>
        </form>

        {/* Toggle mode */}
        <div className="text-center mt-5">
          <span className="text-[12px] text-white/25">
            {mode === "login" ? "Don't have an account?" : "Already have an account?"}
          </span>
          <button
            onClick={() => { setMode(mode === "login" ? "register" : "login"); setLocalError(""); }}
            className="text-[12px] text-violet-400 hover:text-violet-300 ml-1.5 cursor-pointer font-medium"
          >
            {mode === "login" ? "Sign up" : "Sign in"}
          </button>
        </div>
      </div>
    </div>
  );
}
