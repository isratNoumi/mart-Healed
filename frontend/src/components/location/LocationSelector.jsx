import React from "react";
import { getStores, resolveZip } from "../../api/location";
import { useLocation } from "../../context/LocationContext";

export default function LocationSelector() {
  const { location, updateLocation } = useLocation();
  const [zipCode, setZipCode] = React.useState(location ? location.zip_code : "77002");
  const [open, setOpen] = React.useState(false);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState("");
  const [stores, setStores] = React.useState([]);

  React.useEffect(() => {
    if (!open || stores.length) return;
    getStores()
      .then(setStores)
      .catch((requestError) => setError(requestError.message));
  }, [open, stores.length]);

  async function handleSubmit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      updateLocation(await resolveZip(zipCode));
      setOpen(false);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="location-control">
      <button className="location-button" type="button" aria-expanded={open} onClick={() => setOpen(!open)}>
        <span className="location-summary">
          <span className="location-label">{location ? "Delivering to" : "Shopping location"}</span>
          <strong>{location ? location.zip_code : "Choose ZIP"}</strong>
        </span>
        <span className="location-action">{location ? "Change" : "Select"} <span aria-hidden="true">&#9662;</span></span>
      </button>
      {open ? (
        <form className="location-popover" onSubmit={handleSubmit}>
          <strong>Choose your location</strong>
          {location ? <span className="selected-store">{location.store.name}</span> : null}
          <label htmlFor="store-choice">Available stores</label>
          <select id="store-choice" value={zipCode} onChange={(event) => setZipCode(event.target.value)}>
            <option value="">Select a store or ZIP</option>
            {stores.map((store) => <option value={store.zip_code} key={store.id}>{store.name} - {store.city}, {store.state} {store.zip_code}</option>)}
          </select>
          <label htmlFor="zip-code">ZIP code</label>
          <input id="zip-code" inputMode="numeric" maxLength="5" value={zipCode} onChange={(event) => setZipCode(event.target.value)} />
          {error ? <p className="error-message">{error}</p> : null}
          <button type="submit" disabled={loading}>{loading ? "Checking..." : "Update location"}</button>
        </form>
      ) : null}
    </div>
  );
}