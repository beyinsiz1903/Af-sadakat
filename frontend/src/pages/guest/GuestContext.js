import React, { createContext, useContext } from 'react';

const GuestContext = createContext(null);

export function GuestProvider({ value, children }) {
  return <GuestContext.Provider value={value}>{children}</GuestContext.Provider>;
}

export function useGuest() {
  const ctx = useContext(GuestContext);
  if (!ctx) throw new Error('useGuest must be used within GuestProvider');
  return ctx;
}
