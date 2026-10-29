import React from "react";

export const LocationContext = React.createContext(null);

export function LocationProvider({ children }) {
  const [location, setLocation] = React.useState(() => {
    try {
      return JSON.parse(localStorage.getItem("build-mart-location")) || null;
    } catch {
      return null;
    }
  });

  const updateLocation = React.useCallback((nextLocation) => {
    setLocation(nextLocation);
    localStorage.setItem("build-mart-location", JSON.stringify(nextLocation));
  }, []);

  return (
    <LocationContext.Provider value={{ location, updateLocation }}>
      {children}
    </LocationContext.Provider>
  );
}

export function useLocation() {
  return React.useContext(LocationContext);
}