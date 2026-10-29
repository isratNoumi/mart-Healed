import React from "react";
import { Link, useHistory } from "react-router-dom";
import {
  createAddress,
  getAddresses,
  getCheckout,
  getFulfillmentOptions,
  placeOrder,
  processPayment,
  updateAddress,
  validateCheckout
} from "../api/checkout";
import AddressSelector from "../components/checkout/AddressSelector";
import BillingAddressSelector from "../components/checkout/BillingAddressSelector";
import CheckoutError from "../components/checkout/CheckoutError";
import CheckoutProgress from "../components/checkout/CheckoutProgress";
import FulfillmentSelector from "../components/checkout/FulfillmentSelector";
import OrderSummary from "../components/checkout/OrderSummary";
import PaymentError from "../components/checkout/PaymentError";
import PaymentForm from "../components/checkout/PaymentForm";
import PaymentMethodSelector from "../components/checkout/PaymentMethodSelector";
import PaymentProcessing from "../components/checkout/PaymentProcessing";
import StorePickupSelector from "../components/checkout/StorePickupSelector";
import { useCart } from "../context/CartContext";
import { useLocation } from "../context/LocationContext";
import { toCardPayload, validateCardForm } from "../utils/card";

const SHIPPING_TYPES = ["shipping", "both"];
const BILLING_TYPES = ["billing", "both"];
const EMPTY_CARD = { cardholder_name: "", card_number: "", expiry_month: "", expiry_year: "", cvv: "" };
// Shown next to the matching form section instead of in the error banner.
const SELECTION_ISSUES = ["FULFILLMENT_REQUIRED", "PICKUP_STORE_REQUIRED", "SHIPPING_ADDRESS_REQUIRED", "BILLING_ADDRESS_REQUIRED"];
// The draft order was cancelled or no longer matches, so the summary must be refreshed.
const REFRESH_CODES = ["TOTAL_CHANGED", "CHECKOUT_INVALID", "CART_CHANGED", "PRICE_CHANGED", "PRODUCT_UNAVAILABLE", "INSUFFICIENT_INVENTORY", "ORDER_EXPIRED", "ORDER_CANCELLED", "EMPTY_CART"];

function pickDefault(addresses, types) {
  const usable = addresses.filter((address) => types.includes(address.type));
  const preferred = usable.find((address) => address.is_default) || usable[0];
  return preferred ? preferred.id : null;
}

function firstAvailable(options) {
  const order = ["SHIP_TO_HOME", "STORE_PICKUP", "DELIVERY"];
  const option = order.map((type) => options.find((item) => item.type === type)).find((item) => item && item.available);
  return option ? option.type : null;
}

export default function CheckoutPage() {
  const history = useHistory();
  const { location } = useLocation();
  const { refreshCart } = useCart();
  const storeId = location ? location.store.id : null;

  const [loadState, setLoadState] = React.useState("loading");
  const [loadError, setLoadError] = React.useState("");
  const [addresses, setAddresses] = React.useState([]);
  const [paymentMethods, setPaymentMethods] = React.useState([]);
  const [options, setOptions] = React.useState([]);
  const [quote, setQuote] = React.useState(null);
  const [quoting, setQuoting] = React.useState(false);

  const [fulfillmentType, setFulfillmentType] = React.useState(null);
  const [pickupStoreId, setPickupStoreId] = React.useState(null);
  const [shippingAddressId, setShippingAddressId] = React.useState(null);
  const [billingSame, setBillingSame] = React.useState(true);
  const [billingAddressId, setBillingAddressId] = React.useState(null);

  const [paymentChoice, setPaymentChoice] = React.useState("new");
  const [card, setCard] = React.useState(EMPTY_CARD);
  const [cardErrors, setCardErrors] = React.useState({});
  const [saveCard, setSaveCard] = React.useState(false);

  const [stage, setStage] = React.useState("idle");
  const [orderError, setOrderError] = React.useState("");
  const [showSelectionIssues, setShowSelectionIssues] = React.useState(false);
  const [paymentError, setPaymentError] = React.useState(null);

  const mountedRef = React.useRef(true);
  const submittingRef = React.useRef(false);
  const quoteRequestRef = React.useRef(0);
  React.useEffect(() => () => { mountedRef.current = false; }, []);

  const isPickup = fulfillmentType === "STORE_PICKUP";
  const selection = React.useMemo(() => ({
    store_id: storeId,
    fulfillment_type: fulfillmentType,
    pickup_store_id: isPickup ? pickupStoreId : null,
    shipping_address_id: isPickup ? null : shippingAddressId,
    billing_address_id: !isPickup && billingSame ? null : billingAddressId
  }), [storeId, fulfillmentType, isPickup, pickupStoreId, shippingAddressId, billingSame, billingAddressId]);

  const loadCheckout = React.useCallback(async () => {
    if (!storeId) return;
    setLoadState("loading");
    setLoadError("");
    try {
      const data = await getCheckout(storeId);
      if (!mountedRef.current) return;
      setAddresses(data.addresses);
      setPaymentMethods(data.payment_methods);
      setOptions(data.fulfillment_options);
      setQuote(data.quote);
      setShippingAddressId(data.quote.shipping_address_id || pickDefault(data.addresses, SHIPPING_TYPES));
      setBillingAddressId(pickDefault(data.addresses, BILLING_TYPES));
      setFulfillmentType(firstAvailable(data.fulfillment_options));
      const pickup = data.fulfillment_options.find((option) => option.type === "STORE_PICKUP");
      const pickupStore = pickup && (pickup.pickup_stores.find((store) => store.store_id === storeId && store.all_items_available)
        || pickup.pickup_stores.find((store) => store.all_items_available));
      setPickupStoreId(pickupStore ? pickupStore.store_id : null);
      const savedCard = data.payment_methods.find((method) => method.is_default && !method.is_expired)
        || data.payment_methods.find((method) => !method.is_expired);
      setPaymentChoice(savedCard ? savedCard.id : "new");
      setLoadState("ready");
    } catch (error) {
      if (!mountedRef.current) return;
      setLoadError(error.message);
      setLoadState("error");
    }
  }, [storeId]);

  React.useEffect(() => { loadCheckout(); }, [loadCheckout]);

  const refreshQuote = React.useCallback(async () => {
    if (!storeId) return;
    const requestId = ++quoteRequestRef.current;
    setQuoting(true);
    try {
      const result = await validateCheckout(selection);
      if (mountedRef.current && requestId === quoteRequestRef.current) setQuote(result);
    } catch (error) {
      if (mountedRef.current && requestId === quoteRequestRef.current) setOrderError(error.message);
    } finally {
      if (mountedRef.current && requestId === quoteRequestRef.current) setQuoting(false);
    }
  }, [selection, storeId]);

  React.useEffect(() => {
    if (loadState === "ready") refreshQuote();
  }, [loadState, refreshQuote]);

  React.useEffect(() => {
    if (loadState !== "ready" || isPickup) return;
    let active = true;
    getFulfillmentOptions(storeId, shippingAddressId)
      .then((result) => { if (active && mountedRef.current) setOptions(result); })
      .catch(() => {});
    return () => { active = false; };
  }, [loadState, storeId, shippingAddressId, isPickup]);

  async function saveAddress(payload, previousId) {
    const saved = previousId ? await updateAddress(previousId, payload) : await createAddress(payload);
    const refreshed = await getAddresses();
    if (!mountedRef.current) return saved;
    setAddresses(refreshed);
    // Editing an address used by a past order returns a new ID, so follow it.
    if (previousId && shippingAddressId === previousId) setShippingAddressId(saved.id);
    if (previousId && billingAddressId === previousId) setBillingAddressId(saved.id);
    return saved;
  }

  function handleError(error) {
    if (error.status === 402) {
      setPaymentError({
        message: error.message,
        canRetry: error.body.can_retry !== false,
        attemptsRemaining: error.body.attempts_remaining
      });
      setCard((current) => ({ ...current, cvv: "" }));
      return;
    }
    if (error.code === "CARD_INVALID") setCardErrors(error.body.errors || {});
    setOrderError(error.message);
    if (REFRESH_CODES.includes(error.code)) {
      refreshQuote();
      refreshCart();
    }
  }

  async function handlePlaceOrder() {
    if (submittingRef.current || !quote) return;
    setOrderError("");
    setPaymentError(null);
    setShowSelectionIssues(true);

    let errors = {};
    if (paymentChoice === "new") errors = validateCardForm(card);
    setCardErrors(errors);
    if (Object.keys(errors).length) {
      setOrderError("Please check your card details.");
      return;
    }
    if (!quote.can_place_order) {
      setOrderError("Please fix the items highlighted above before placing your order.");
      return;
    }

    submittingRef.current = true;
    setStage("placing");
    try {
      const order = await placeOrder({ ...selection, expected_total: quote.total });
      if (mountedRef.current) setStage("paying");
      const payment = paymentChoice === "new"
        ? { order_id: order.order_id, card: toCardPayload(card), save_card: saveCard }
        : { order_id: order.order_id, payment_method_id: paymentChoice };
      const result = await processPayment(payment);
      refreshCart();
      history.replace(`/order-confirmation/${result.order_id}`);
    } catch (error) {
      if (mountedRef.current) handleError(error);
    } finally {
      submittingRef.current = false;
      if (mountedRef.current) setStage("idle");
    }
  }

  if (!storeId) {
    return (
      <section className="checkout-page">
        <h1>Checkout</h1>
        <div className="empty-state">
          <p>Choose your store using <strong>Shopping location</strong> at the top of the page so we can confirm prices and stock.</p>
        </div>
      </section>
    );
  }

  if (loadState === "loading") return <section className="checkout-page"><h1>Checkout</h1><p className="page-status" role="status">Loading checkout...</p></section>;

  if (loadState === "error") {
    return (
      <section className="checkout-page">
        <h1>Checkout</h1>
        <div className="error-message" role="alert"><p>{loadError}</p></div>
        <button className="button" type="button" onClick={loadCheckout}>Try again</button>
      </section>
    );
  }

  if (!quote.lines.length) {
    return (
      <section className="checkout-page">
        <h1>Checkout</h1>
        <div className="empty-state">
          <p>Your cart is empty.</p>
          <Link className="button" to="/products">Shop products</Link>
        </div>
      </section>
    );
  }

  const issueCodes = quote.issues.filter((issue) => issue.blocking).map((issue) => issue.code);
  const bannerIssues = quote.issues.filter((issue) => !SELECTION_ISSUES.includes(issue.code) || showSelectionIssues);
  const pickupOption = options.find((option) => option.type === "STORE_PICKUP");
  const productNames = quote.lines.reduce((names, line) => ({ ...names, [line.product_id]: line.product_name }), {});
  const billingResolved = Boolean(quote.billing_address_id);
  const busy = stage !== "idle";
  const steps = [
    { label: "Delivery", complete: Boolean(fulfillmentType) && !issueCodes.some((code) => ["PICKUP_STORE_REQUIRED", "PICKUP_STORE_INVALID", "SHIPPING_ADDRESS_REQUIRED", "DELIVERY_OUT_OF_AREA"].includes(code)) },
    { label: "Billing", complete: billingResolved },
    { label: "Payment", complete: paymentChoice !== "new" || Boolean(card.card_number && card.cvv) },
    { label: "Review", complete: false }
  ];

  return (
    <section className="checkout-page">
      <PaymentProcessing stage={stage} />
      <Link className="back-link" to="/cart">← Return to cart</Link>
      <h1>Checkout</h1>
      <CheckoutProgress steps={steps} />

      <div className="checkout-layout">
        <div className="checkout-main">
          <CheckoutError message={orderError} issues={bannerIssues} />
          <PaymentError error={paymentError} />

          <section className="checkout-section" aria-labelledby="delivery-heading">
            <h2 id="delivery-heading">1. Delivery</h2>
            <FulfillmentSelector options={options} value={fulfillmentType} onChange={setFulfillmentType} disabled={busy} />
            {isPickup && pickupOption ? (
              <StorePickupSelector stores={pickupOption.pickup_stores} value={pickupStoreId} onChange={setPickupStoreId} productNames={productNames} disabled={busy} />
            ) : null}
            {fulfillmentType && !isPickup ? (
              <>
                <h3 className="section-label">Shipping address</h3>
                <AddressSelector
                  name="shipping-address"
                  label="Shipping address"
                  addresses={addresses}
                  allowedTypes={SHIPPING_TYPES}
                  value={shippingAddressId}
                  onChange={setShippingAddressId}
                  onSave={saveAddress}
                  disabled={busy}
                />
              </>
            ) : null}
          </section>

          <section className="checkout-section" aria-labelledby="billing-heading">
            <h2 id="billing-heading">2. Billing address</h2>
            <BillingAddressSelector
              allowSameAsShipping={!isPickup}
              sameAsShipping={billingSame}
              onSameChange={setBillingSame}
              addresses={addresses}
              value={billingAddressId}
              onChange={setBillingAddressId}
              onSave={saveAddress}
              disabled={busy}
            />
          </section>

          <section className="checkout-section" aria-labelledby="payment-heading">
            <h2 id="payment-heading">3. Payment</h2>
            <PaymentMethodSelector methods={paymentMethods} value={paymentChoice} onChange={setPaymentChoice} disabled={busy} />
            {paymentChoice === "new" ? (
              <PaymentForm card={card} onChange={setCard} errors={cardErrors} saveCard={saveCard} onSaveCardChange={setSaveCard} disabled={busy} />
            ) : null}
          </section>
        </div>

        <OrderSummary quote={quote} updating={quoting}>
          <button className="button place-order-button" type="button" onClick={handlePlaceOrder} disabled={busy || quoting}>
            {stage === "placing" ? "Placing order..." : stage === "paying" ? "Processing payment..." : "Place order"}
          </button>
          <p className="field-hint">You'll only be charged once your payment is approved.</p>
        </OrderSummary>
      </div>
    </section>
  );
}
