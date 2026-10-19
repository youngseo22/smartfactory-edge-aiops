/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Outfit", "Inter", "system-ui", "sans-serif"],
        mono: ["'JetBrains Mono'", "ui-monospace", "monospace"],
      },
      colors: {
        ink: { 950: "#05070d", 900: "#0a0f1c", 850: "#0e1526", 800: "#131c31" },
        neon: {
          cyan: "#22d3ee",
          teal: "#2dd4bf",
          lime: "#a3e635",
          amber: "#fbbf24",
          coral: "#fb7185",
          violet: "#a78bfa",
        },
      },
      boxShadow: {
        glow: "0 0 24px -4px rgba(34,211,238,.55)",
        "glow-red": "0 0 28px -2px rgba(251,113,133,.75)",
        "glow-amber": "0 0 24px -4px rgba(251,191,36,.7)",
        "glow-lime": "0 0 24px -4px rgba(163,230,53,.65)",
        inset: "inset 0 1px 0 0 rgba(255,255,255,.06), inset 0 -1px 0 0 rgba(0,0,0,.4)",
      },
      keyframes: {
        conveyor: { "0%": { transform: "translateX(-10%)" }, "100%": { transform: "translateX(110%)" } },
        belt: { "0%": { backgroundPosition: "0 0" }, "100%": { backgroundPosition: "-40px 0" } },
        shake: {
          "0%,100%": { transform: "translate(0,0) rotate(0)" },
          "20%": { transform: "translate(-3px,1px) rotate(-2deg)" },
          "40%": { transform: "translate(3px,-1px) rotate(2deg)" },
          "60%": { transform: "translate(-2px,-2px) rotate(-1deg)" },
          "80%": { transform: "translate(2px,2px) rotate(1deg)" },
        },
        blink: { "0%,100%": { opacity: 1 }, "50%": { opacity: 0.25 } },
        dash: { to: { strokeDashoffset: "-40" } },
        scan: { "0%": { transform: "translateY(-100%)" }, "100%": { transform: "translateY(100%)" } },
        wave: { "0%": { transform: "translateX(0)" }, "100%": { transform: "translateX(-50%)" } },
      },
      animation: {
        conveyor: "conveyor linear infinite",
        belt: "belt .6s linear infinite",
        shake: "shake .12s linear infinite",
        blink: "blink 1s ease-in-out infinite",
        dash: "dash 0.8s linear infinite",
        scan: "scan 3s linear infinite",
        wave: "wave 2.2s linear infinite",
        "spin-slow": "spin 2.4s linear infinite",
        "spin-fast": "spin .35s linear infinite",
      },
    },
  },
  plugins: [],
};
