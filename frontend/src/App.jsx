import React from "react";
import { BrowserRouter, Route, Switch } from "react-router-dom";
import RequireAuth from "./components/auth/RequireAuth";
import PageShell from "./components/layout/PageShell";
import { AuthProvider } from "./context/AuthContext";
import { CartProvider } from "./context/CartContext";
import { LocationProvider } from "./context/LocationContext";
import AccountPage from "./pages/AccountPage";
import CartPage from "./pages/CartPage";
import CheckoutPage from "./pages/CheckoutPage";
import HomePage from "./pages/HomePage";
import LoginPage from "./pages/LoginPage";
import NotFoundPage from "./pages/NotFoundPage";
import OrderConfirmationPage from "./pages/OrderConfirmationPage";
import OrderDetailsPage from "./pages/OrderDetailsPage";
import OrderHistoryPage from "./pages/OrderHistoryPage";
import ProductDetailsPage from "./pages/ProductDetailsPage";
import ProductListingPage from "./pages/ProductListingPage";
import RegisterPage from "./pages/RegisterPage";
import "./styles/global.css";

function Protected({ children }) {
  return <RequireAuth>{children}</RequireAuth>;
}

export default function App() {
  return (
    <BrowserRouter>
      <LocationProvider>
        <AuthProvider>
          <CartProvider>
            <PageShell>
              <Switch>
                <Route exact path="/" component={HomePage} />
                <Route exact path={["/products", "/category/:slug"]} component={ProductListingPage} />
                <Route path="/products/:id" component={ProductDetailsPage} />
                <Route path="/cart" component={CartPage} />
                <Route path="/login" component={LoginPage} />
                <Route path="/register" component={RegisterPage} />
                <Route path="/checkout"><Protected><CheckoutPage /></Protected></Route>
                <Route path="/order-confirmation/:orderId"><Protected><OrderConfirmationPage /></Protected></Route>
                <Route exact path="/account"><Protected><AccountPage /></Protected></Route>
                <Route exact path="/account/orders"><Protected><OrderHistoryPage /></Protected></Route>
                <Route path="/account/orders/:orderId"><Protected><OrderDetailsPage /></Protected></Route>
                <Route component={NotFoundPage} />
              </Switch>
            </PageShell>
          </CartProvider>
        </AuthProvider>
      </LocationProvider>
    </BrowserRouter>
  );
}