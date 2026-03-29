import NextAuth from "next-auth";
import Google from "next-auth/providers/google";
import Credentials from "next-auth/providers/credentials";

/** Which providers are available based on env vars */
export function getAvailableProviders() {
  const hasGoogle = !!(process.env.GOOGLE_CLIENT_ID && process.env.GOOGLE_CLIENT_SECRET);
  const hasCredentials = !!(process.env.UI_USERNAME && process.env.UI_PASSWORD);
  return { hasGoogle, hasCredentials, hasAny: hasGoogle || hasCredentials };
}

const providers = [];

// Google OAuth provider
if (process.env.GOOGLE_CLIENT_ID && process.env.GOOGLE_CLIENT_SECRET) {
  providers.push(
    Google({
      clientId: process.env.GOOGLE_CLIENT_ID,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET,
    })
  );
}

// Credentials provider (username/password)
if (process.env.UI_USERNAME && process.env.UI_PASSWORD) {
  providers.push(
    Credentials({
      name: "Credentials",
      credentials: {
        username: { label: "Username", type: "text" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        if (
          credentials?.username === process.env.UI_USERNAME &&
          credentials?.password === process.env.UI_PASSWORD
        ) {
          return { id: "admin", name: "Admin", email: "admin@local" };
        }
        return null;
      },
    })
  );
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers,
  pages: {
    signIn: "/login",
    error: "/auth-error",
  },
  callbacks: {
    async signIn({ user, account }) {
      // For Google auth, check allowed emails
      if (account?.provider === "google") {
        const allowed = process.env.GOOGLE_ALLOWED_EMAILS;
        if (!allowed) return false;
        const allowedList = allowed.split(",").map((e) => e.trim().toLowerCase());
        return allowedList.includes(user.email?.toLowerCase() ?? "");
      }
      return true;
    },
  },
  trustHost: true,
});
