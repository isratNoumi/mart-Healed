import React from "react";
import { Link, useHistory } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function AccountPage() {
  const { user, signOut } = useAuth();
  const history = useHistory();
  const [signingOut, setSigningOut] = React.useState(false);

  async function handleSignOut() {
    setSigningOut(true);
    await signOut();
    history.push("/");
  }

  return (
    <section className="account-page">
      <p className="eyebrow">YOUR ACCOUNT</p>
      <h1>Hi, {user.first_name}</h1>
      <div className="account-grid">
        <div className="account-card">
          <h2>Profile</h2>
          <p>{user.first_name} {user.last_name}</p>
          <p className="muted">{user.email}</p>
        </div>
        <Link className="account-card account-link" to="/account/orders">
          <h2>Your orders</h2>
          <p className="muted">Track and review past purchases.</p>
        </Link>
      </div>
      <button className="secondary-button" type="button" onClick={handleSignOut} disabled={signingOut}>{signingOut ? "Signing out..." : "Sign out"}</button>
    </section>
  );
}
