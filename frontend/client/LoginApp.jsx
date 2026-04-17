import { tokens as t } from "./tokens.js";
import { LoginScreen } from "./screens/LoginScreen.jsx";
import { GlobalStyles } from "./DiagnosisApp.jsx";

/**
 * LoginApp — minimal shell for the /login route.
 *
 * Renders just the login screen with the shared GlobalStyles so fonts
 * and animations match the rest of MarketLens. No header, no footer —
 * a login page is a focal surface, not a chrome-heavy one.
 */
export default function LoginApp() {
  return (
    <div style={{ minHeight: "100vh", background: t.color.canvas, fontFamily: t.font.body }}>
      <GlobalStyles />
      <LoginScreen />
    </div>
  );
}
