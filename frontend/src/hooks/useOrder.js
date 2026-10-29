import React from "react";
import { getOrder } from "../api/orders";

export default function useOrder(orderId) {
  const [state, setState] = React.useState({ loading: true, order: null, error: null });

  const load = React.useCallback(() => {
    let active = true;
    setState({ loading: true, order: null, error: null });
    getOrder(orderId)
      .then((order) => { if (active) setState({ loading: false, order, error: null }); })
      .catch((error) => { if (active) setState({ loading: false, order: null, error }); });
    return () => { active = false; };
  }, [orderId]);

  React.useEffect(load, [load]);
  return { ...state, reload: load };
}
