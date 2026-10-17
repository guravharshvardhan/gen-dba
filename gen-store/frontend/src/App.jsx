import { useEffect, useMemo, useState } from "react";

const API = "http://127.0.0.1:8010";

const money = (value) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0
  }).format(Number(value || 0));

function App() {
  // =========================================================
  // PRODUCT STATE
  // =========================================================

  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState("");
  const [search, setSearch] = useState("");

  const [loading, setLoading] = useState(true);
  const [dbOnline, setDbOnline] = useState(false);

  // =========================================================
  // PAGE STATE
  // =========================================================

  const [page, setPage] = useState("home");

  // =========================================================
  // CART STATE
  // =========================================================

  const [cart, setCart] = useState([]);
  const [cartOpen, setCartOpen] = useState(false);

  // =========================================================
  // PRODUCT MODAL
  // =========================================================

  const [selectedProduct, setSelectedProduct] = useState(null);

  // =========================================================
  // CUSTOMER STATE
  // =========================================================

  const [customers, setCustomers] = useState([]);
  const [customerCity, setCustomerCity] = useState("");
  const [customerLoading, setCustomerLoading] = useState(false);

  // =========================================================
  // CHECKOUT STATE
  // =========================================================

  const [checkoutOpen, setCheckoutOpen] = useState(false);

  const [checkout, setCheckout] = useState({
    name: "",
    email: "",
    city: ""
  });

  const [orderResult, setOrderResult] = useState(null);

  // =========================================================
  // TOAST
  // =========================================================

  const [toast, setToast] = useState("");

  // =========================================================
  // CART CALCULATIONS
  // =========================================================

  const cartCount = useMemo(
    () =>
      cart.reduce(
        (total, item) =>
          total + item.quantity,
        0
      ),
    [cart]
  );

  const cartTotal = useMemo(
    () =>
      cart.reduce(
        (total, item) =>
          total +
          Number(item.price) *
            item.quantity,
        0
      ),
    [cart]
  );

  // =========================================================
  // LOAD PRODUCTS
  // =========================================================

  const loadProducts = async (
    overrideSearch = search,
    overrideCategory = selectedCategory
  ) => {
    setLoading(true);

    try {
      const query = new URLSearchParams();

      const cleanSearch =
        overrideSearch.trim();

      const cleanCategory =
        overrideCategory.trim();

      if (cleanSearch) {
        query.set(
          "search",
          cleanSearch
        );
      }

      if (cleanCategory) {
        query.set(
          "category",
          cleanCategory
        );
      }

      const response = await fetch(
        `${API}/api/products?${query.toString()}`
      );

      if (!response.ok) {
        throw new Error(
          "Product service unavailable."
        );
      }

      const data =
        await response.json();

      setProducts(data);
      setDbOnline(true);

      return data;
    } catch (error) {
      setDbOnline(false);
      setToast(error.message);

      return [];
    } finally {
      setLoading(false);
    }
  };

  // =========================================================
  // LOAD CATEGORIES
  // =========================================================

  const loadCategories = async () => {
    try {
      const response = await fetch(
        `${API}/api/categories`
      );

      if (!response.ok) {
        throw new Error(
          "Category service unavailable."
        );
      }

      const data =
        await response.json();

      setCategories(data);
    } catch (error) {
      console.error(
        "Category loading error:",
        error
      );
    }
  };

  // =========================================================
  // DATABASE HEALTH
  // =========================================================

  const checkHealth = async () => {
    try {
      const response = await fetch(
        `${API}/api/health`
      );

      setDbOnline(response.ok);
    } catch {
      setDbOnline(false);
    }
  };

  // =========================================================
  // INITIAL LOAD
  // =========================================================

  useEffect(() => {
    loadCategories();
    checkHealth();
    loadProducts();
  }, []);

  // =========================================================
  // AUTO PRODUCT SEARCH
  // =========================================================

  useEffect(() => {
    if (
      page !== "home" &&
      page !== "products"
    ) {
      return;
    }

    const timeout =
      setTimeout(() => {
        loadProducts(
          search,
          selectedCategory
        );
      }, 350);

    return () => {
      clearTimeout(timeout);
    };
  }, [
    search,
    selectedCategory,
    page
  ]);

  // =========================================================
  // TOAST AUTO HIDE
  // =========================================================

  useEffect(() => {
    if (!toast) {
      return;
    }

    const timeout =
      setTimeout(() => {
        setToast("");
      }, 2600);

    return () => {
      clearTimeout(timeout);
    };
  }, [toast]);

  // =========================================================
  // HEADER SEARCH
  // =========================================================

  const handleProductSearch = async (
    event
  ) => {
    event?.preventDefault();

    setPage("products");

    await loadProducts(
      search,
      selectedCategory
    );

    window.scrollTo({
      top: 0,
      behavior: "smooth"
    });
  };

  // =========================================================
  // CATEGORY CHANGE
  // =========================================================

  const handleCategoryChange = (
    category
  ) => {
    setSelectedCategory(category);
    setPage(
      category
        ? "products"
        : "home"
    );
  };

  // =========================================================
  // NAVIGATION
  // =========================================================

  const goHome = () => {
    setSearch("");
    setSelectedCategory("");
    setPage("home");
    window.scrollTo({
      top: 0,
      behavior: "smooth"
    });
  };

  const showProducts = () => {
    setPage("products");
    window.scrollTo({
      top: 0,
      behavior: "smooth"
    });
  };

  const showCustomers = () => {
    setPage("customers");
    window.scrollTo({
      top: 0,
      behavior: "smooth"
    });
  };

  // =========================================================
  // CART
  // =========================================================

  const addToCart = (
    product
  ) => {
    if (
      Number(product.stock) <= 0
    ) {
      setToast(
        "This product is currently out of stock."
      );

      return;
    }

    setCart((current) => {
      const exists =
        current.find(
          (item) =>
            item.product_id ===
            product.product_id
        );

      if (exists) {
        return current.map(
          (item) =>
            item.product_id ===
            product.product_id
              ? {
                  ...item,
                  quantity:
                    item.quantity + 1
                }
              : item
        );
      }

      return [
        ...current,
        {
          ...product,
          quantity: 1
        }
      ];
    });

    setToast(
      `${product.name} added to cart`
    );
  };

  const changeQuantity = (
    productId,
    amount
  ) => {
    setCart((current) =>
      current
        .map((item) =>
          item.product_id ===
          productId
            ? {
                ...item,
                quantity:
                  Math.max(
                    0,
                    item.quantity +
                      amount
                  )
              }
            : item
        )
        .filter(
          (item) =>
            item.quantity > 0
        )
    );
  };

  // =========================================================
  // PRODUCT DETAILS
  // =========================================================

  const openProduct = async (
    productId
  ) => {
    try {
      const response =
        await fetch(
          `${API}/api/products/${productId}`
        );

      const data =
        await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
            "Product unavailable."
        );
      }

      setSelectedProduct(data);
    } catch (error) {
      setToast(error.message);
    }
  };

  // =========================================================
  // CUSTOMER SEARCH
  // =========================================================

  const searchCustomers = async (
    event
  ) => {
    event?.preventDefault();

    setCustomerLoading(true);

    try {
      const city =
        customerCity.trim();

      const response =
        await fetch(
          `${API}/api/customers?city=${encodeURIComponent(
            city
          )}`
        );

      const data =
        await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
            "Customer search failed."
        );
      }

      setCustomers(data);
      setDbOnline(true);

      if (city) {
        setToast(
          `${data.length} customers found in ${city}`
        );
      } else {
        setToast(
          "Showing recent customers"
        );
      }
    } catch (error) {
      setToast(error.message);
    } finally {
      setCustomerLoading(false);
    }
  };

  // =========================================================
  // CHECKOUT
  // =========================================================

  const submitOrder = async (
    event
  ) => {
    event.preventDefault();

    if (!cart.length) {
      setToast(
        "Your cart is empty."
      );

      return;
    }

    try {
      const response =
        await fetch(
          `${API}/api/orders`,
          {
            method: "POST",
            headers: {
              "Content-Type":
                "application/json"
            },
            body: JSON.stringify({
              ...checkout,
              items: cart.map(
                (item) => ({
                  product_id:
                    item.product_id,
                  quantity:
                    item.quantity
                })
              )
            })
          }
        );

      const data =
        await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
            "Order failed."
        );
      }

      setOrderResult(data);

      setCart([]);

      setCheckoutOpen(false);

      setCartOpen(false);

      setCheckout({
        name: "",
        email: "",
        city: ""
      });

      setToast(
        "Order placed successfully"
      );

      await loadProducts();
    } catch (error) {
      setToast(error.message);
    }
  };

  const heroProduct =
    products[0];

  return (
    <div className="store-app">

      {/* =====================================================
          HEADER
      ===================================================== */}

      <header className="store-header">

        <div className="header-main">

          {/* LOGO */}

          <button
            className="store-logo"
            onClick={goHome}
          >

            <span className="logo-mark">
              G
            </span>

            <span>
              <strong>
                GenStore
              </strong>

              <small>
                Smart commerce
              </small>
            </span>

          </button>


          {/* LOCATION */}

          <div className="location-pill">

            <span className="location-icon">
              ⌖
            </span>

            <span>

              <small>
                Deliver to
              </small>

              <strong>
                India
              </strong>

            </span>

          </div>


          {/* PRODUCT SEARCH */}

          <form
            className="search-box"
            onSubmit={
              handleProductSearch
            }
          >

            <select
              value={selectedCategory}
              onChange={(event) =>
                handleCategoryChange(
                  event.target.value
                )
              }
              aria-label="Product category"
            >

              <option value="">
                All
              </option>

              {categories.map(
                (category) => (
                  <option
                    key={category}
                    value={category}
                  >
                    {category}
                  </option>
                )
              )}

            </select>


            <input
              value={search}
              onChange={(event) =>
                setSearch(
                  event.target.value
                )
              }
              onKeyDown={(event) => {
                if (
                  event.key ===
                  "Enter"
                ) {
                  handleProductSearch(
                    event
                  );
                }
              }}
              placeholder="Search products, brands and more"
              aria-label="Search products"
            />


            <button
              type="submit"
              aria-label="Search products"
            >
              ⌕
            </button>

          </form>


          {/* CUSTOMER */}

          <button
            className="header-link"
            onClick={
              showCustomers
            }
          >

            <small>
              Hello, support
            </small>

            <strong>
              Customers ↗
            </strong>

          </button>


          {/* CART */}

          <button
            className="cart-button"
            onClick={() =>
              setCartOpen(true)
            }
          >

            <span className="cart-icon">
              ▣
            </span>

            <span className="cart-count">
              {cartCount}
            </span>

            <strong>
              Cart
            </strong>

          </button>

        </div>


        {/* CATEGORY BAR */}

        <div className="category-bar">

          <button
            onClick={goHome}
          >
            ☰ All
          </button>


          <button
            onClick={() => {
              setSearch("");
              setSelectedCategory("");
              showProducts();
            }}
          >
            New arrivals
          </button>


          <button
            onClick={() =>
              handleCategoryChange(
                "Electronics"
              )
            }
          >
            Electronics
          </button>


          <button
            onClick={() =>
              handleCategoryChange(
                "Accessories"
              )
            }
          >
            Accessories
          </button>


          <button
            onClick={() =>
              handleCategoryChange(
                "Fashion"
              )
            }
          >
            Fashion
          </button>


          <button
            onClick={() =>
              handleCategoryChange(
                "Home"
              )
            }
          >
            Home
          </button>


          <button
            onClick={
              showCustomers
            }
          >
            Customer search
          </button>


          <span className="bar-spacer" />


          <span
            className={`db-status ${
              dbOnline
                ? "online"
                : "offline"
            }`}
          >

            <i />

            {dbOnline
              ? "Database connected"
              : "Database offline"}

          </span>

        </div>

      </header>


      {/* =====================================================
          MAIN
      ===================================================== */}

      <main>

        {/* CUSTOMER WORKSPACE */}

        {page ===
        "customers" ? (

          <CustomerWorkspace
            city={
              customerCity
            }
            setCity={
              setCustomerCity
            }
            customers={
              customers
            }
            loading={
              customerLoading
            }
            onSearch={
              searchCustomers
            }
          />

        ) : page ===
          "products" ? (

          /* ===================================================
             PRODUCT RESULTS PAGE
          =================================================== */

          <section className="workspace">

            <div className="workspace-header">

              <div>

                <span className="eyebrow">
                  PRODUCT DISCOVERY
                </span>

                <h1>
                  {search
                    ? `Results for "${search}"`
                    : selectedCategory
                    ? selectedCategory
                    : "Shop all products"}
                </h1>

                <p>
                  Explore products from the
                  live GenStore catalog.
                </p>

              </div>

              <div className="workspace-chip">
                LIVE DATABASE
              </div>

            </div>


            <div className="customer-search-panel">

              <div>

                <span className="eyebrow">
                  SMART SEARCH
                </span>

                <h2>
                  Find what you need
                </h2>

                <p>
                  Search the live product
                  catalog by name or category.
                </p>

              </div>


              <form
                className="customer-search-form"
                onSubmit={
                  handleProductSearch
                }
              >

                <input
                  value={search}
                  onChange={(event) =>
                    setSearch(
                      event.target.value
                    )
                  }
                  placeholder="Search products..."
                />

                <button type="submit">
                  Search products →
                </button>

              </form>

            </div>


            {loading ? (

              <ProductSkeleton />

            ) : products.length ? (

              <div className="product-grid">

                {products.map(
                  (product) => (
                    <ProductCard
                      key={
                        product.product_id
                      }
                      product={
                        product
                      }
                      onAdd={
                        addToCart
                      }
                      onOpen={
                        openProduct
                      }
                    />
                  )
                )}

              </div>

            ) : (

              <div className="customer-empty">

                No products found.

                <button
                  className="text-link"
                  onClick={
                    goHome
                  }
                >
                  Back to home →
                </button>

              </div>

            )}

          </section>

        ) : (

          /* ===================================================
             HOME PAGE
          =================================================== */

          <>

            {/* HERO */}

            <section className="hero-section">

              <div className="hero-copy">

                <span className="eyebrow">
                  SMART SHOPPING, BUILT FOR REAL LIFE
                </span>

                <h1>
                  Everything you need.
                  <br />
                  <span>
                    One smarter storefront.
                  </span>
                </h1>

                <p>
                  Discover hand-picked tech,
                  everyday essentials and
                  lifestyle upgrades with fast
                  browsing and a seamless
                  checkout experience.
                </p>


                <div className="hero-actions">

                  <button
                    className="primary-cta"
                    onClick={
                      showProducts
                    }
                  >
                    Shop the collection →
                  </button>


                  <button
                    className="secondary-cta"
                    onClick={() =>
                      handleCategoryChange(
                        "Electronics"
                      )
                    }
                  >
                    Explore tech
                  </button>

                </div>


                <div className="hero-proof">

                  <span>
                    ✓ Secure checkout
                  </span>

                  <span>
                    ✓ Easy returns
                  </span>

                  <span>
                    ✓ Live inventory
                  </span>

                </div>

              </div>


              <div className="hero-feature">

                {heroProduct ? (

                  <>

                    <div className="hero-product-glow" />

                    {heroProduct.image_url ? (
                      <img
                        src={
                          heroProduct.image_url
                        }
                        alt={
                          heroProduct.name
                        }
                      />
                    ) : (
                      <div className="hero-skeleton" />
                    )}


                    <div className="hero-feature-card">

                      <div>

                        <span>
                          Featured today
                        </span>

                        <strong>
                          {heroProduct.name}
                        </strong>

                      </div>

                      <b>
                        {money(
                          heroProduct.price
                        )}
                      </b>

                    </div>

                  </>

                ) : (

                  <div className="hero-skeleton" />

                )}

              </div>

            </section>


            {/* TRUST STRIP */}

            <section className="trust-strip">

              <div>

                <span>
                  ▣
                </span>

                <div>

                  <strong>
                    Fast delivery
                  </strong>

                  <small>
                    Reliable nationwide shipping
                  </small>

                </div>

              </div>


              <div>

                <span>
                  ◇
                </span>

                <div>

                  <strong>
                    Curated quality
                  </strong>

                  <small>
                    Products worth your money
                  </small>

                </div>

              </div>


              <div>

                <span>
                  ✓
                </span>

                <div>

                  <strong>
                    Secure checkout
                  </strong>

                  <small>
                    Transactions handled safely
                  </small>

                </div>

              </div>


              <div>

                <span>
                  ↺
                </span>

                <div>

                  <strong>
                    Simple returns
                  </strong>

                  <small>
                    Easy customer support
                  </small>

                </div>

              </div>

            </section>


            {/* TOP PICKS */}

            <section className="section-block">

              <div className="section-heading">

                <div>

                  <span className="eyebrow">
                    TOP PICKS
                  </span>

                  <h2>
                    Trending right now
                  </h2>

                  <p>
                    Fresh picks from the
                    GenStore catalog.
                  </p>

                </div>


                <button
                  className="text-link"
                  onClick={
                    showProducts
                  }
                >
                  View all →
                </button>

              </div>


              {loading ? (

                <ProductSkeleton />

              ) : (

                <div className="product-grid">

                  {products
                    .slice(0, 8)
                    .map(
                      (product) => (
                        <ProductCard
                          key={
                            product.product_id
                          }
                          product={
                            product
                          }
                          onAdd={
                            addToCart
                          }
                          onOpen={
                            openProduct
                          }
                        />
                      )
                    )}

                </div>

              )}

            </section>


            {/* COLLECTIONS */}

            <section className="collections-section">

              <div className="section-heading">

                <div>

                  <span className="eyebrow">
                    SHOP BY WORLD
                  </span>

                  <h2>
                    Made for every part of your day
                  </h2>

                </div>

              </div>


              <div className="collection-grid">

                <CollectionCard
                  title="Desk setup"
                  subtitle="Sharper workspaces"
                  image="https://images.unsplash.com/photo-1497366754035-f200968a6e72?auto=format&fit=crop&w=1200&q=80"
                  onClick={() =>
                    handleCategoryChange(
                      "Electronics"
                    )
                  }
                />


                <CollectionCard
                  title="Travel light"
                  subtitle="Built to move"
                  image="https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1200&q=80"
                  onClick={
                    showProducts
                  }
                />


                <CollectionCard
                  title="Everyday style"
                  subtitle="Easy, elevated essentials"
                  image="https://images.unsplash.com/photo-1529139574466-a303027c1d8b?auto=format&fit=crop&w=1200&q=80"
                  onClick={() =>
                    handleCategoryChange(
                      "Fashion"
                    )
                  }
                />

              </div>

            </section>


            {/* GEN-DBA CONNECTION BANNER */}

            <section className="insights-banner">

              <div>

                <span className="eyebrow">
                  POWERED BY A LIVE DATABASE
                </span>

                <h2>
                  Every click creates real workload.
                </h2>

                <p>
                  GenStore runs on the same
                  PostgreSQL database connected to
                  Gen-DBA, turning normal shopping
                  activity into a realistic
                  performance-monitoring workload.
                </p>

              </div>


              <button
                onClick={
                  showCustomers
                }
              >
                Open customer workspace →
              </button>

            </section>

          </>

        )}

      </main>


      {/* =====================================================
          FOOTER
      ===================================================== */}

      <footer className="store-footer">

        <div className="footer-brand">

          <div className="logo-mark">
            G
          </div>

          <div>

            <strong>
              GenStore
            </strong>

            <span>
              Smart commerce demo platform
            </span>

          </div>

        </div>


        <div className="footer-meta">

          <span>
            © 2026 GenStore
          </span>

          <span>
            Live PostgreSQL workload
          </span>

          <span>
            Connected to Gen-DBA
          </span>

        </div>

      </footer>


      {/* =====================================================
          PRODUCT MODAL
      ===================================================== */}

      {selectedProduct && (

        <ProductModal
          product={
            selectedProduct
          }

          onClose={() =>
            setSelectedProduct(
              null
            )
          }

          onAdd={() => {

            addToCart(
              selectedProduct
            );

            setSelectedProduct(
              null
            );

          }}
        />

      )}


      {/* =====================================================
          CART DRAWER
      ===================================================== */}

      {cartOpen && (

        <CartDrawer
          cart={cart}
          total={cartTotal}

          onClose={() =>
            setCartOpen(false)
          }

          onChange={
            changeQuantity
          }

          onCheckout={() => {

            if (!cart.length) {
              setToast(
                "Your cart is empty."
              );

              return;
            }

            setCartOpen(false);
            setCheckoutOpen(true);

          }}
        />

      )}


      {/* =====================================================
          CHECKOUT
      ===================================================== */}

      {checkoutOpen && (

        <CheckoutModal
          data={checkout}
          setData={
            setCheckout
          }

          onClose={() =>
            setCheckoutOpen(
              false
            )
          }

          onSubmit={
            submitOrder
          }
        />

      )}


      {/* =====================================================
          ORDER SUCCESS
      ===================================================== */}

      {orderResult && (

        <div className="success-overlay">

          <div className="success-card">

            <div className="success-check">
              ✓
            </div>

            <span className="eyebrow">
              ORDER CONFIRMED
            </span>

            <h2>
              Thanks, your order is on the way.
            </h2>

            <p>
              Your order #
              {orderResult.order_id}
              {" "}
              has been created successfully.
            </p>

            <strong>
              {money(
                orderResult.total_amount
              )}
            </strong>

            <button
              className="primary-cta"
              onClick={() =>
                setOrderResult(
                  null
                )
              }
            >
              Continue shopping
            </button>

          </div>

        </div>

      )}


      {/* =====================================================
          TOAST
      ===================================================== */}

      {toast && (
        <div className="toast">
          {toast}
        </div>
      )}

    </div>
  );
}


/* =========================================================
   PRODUCT CARD
========================================================= */

function ProductCard({
  product,
  onAdd,
  onOpen
}) {
  return (
    <article className="product-card">

      <button
        className="product-image-wrap"
        onClick={() =>
          onOpen(
            product.product_id
          )
        }
      >

        {product.image_url ? (

          <img
            src={
              product.image_url
            }
            alt={
              product.name
            }
          />

        ) : (

          <div className="image-placeholder">
            GS
          </div>

        )}

        <span className="image-tag">
          {product.category}
        </span>

      </button>


      <div className="product-content">

        <span className="product-category">
          {product.category}
        </span>


        <button
          className="product-title"
          onClick={() =>
            onOpen(
              product.product_id
            )
          }
        >
          {product.name}
        </button>


        <div className="rating-row">

          <span>
            ★
          </span>

          <b>
            {Number(
              product.rating || 4.5
            ).toFixed(1)}
          </b>

          <small>
            ({product.reviews_count || 0})
          </small>

        </div>


        <div className="price-row">

          <strong>
            {money(
              product.price
            )}
          </strong>

          <span>
            {Number(
              product.stock
            ) > 0
              ? `${product.stock} left`
              : "Out of stock"}
          </span>

        </div>


        <button
          className="add-button"
          onClick={() =>
            onAdd(product)
          }
          disabled={
            Number(
              product.stock
            ) <= 0
          }
        >
          Add to cart
        </button>

      </div>

    </article>
  );
}


/* =========================================================
   COLLECTION CARD
========================================================= */

function CollectionCard({
  title,
  subtitle,
  image,
  onClick
}) {
  return (
    <button
      className="collection-card"
      onClick={onClick}
    >

      <img
        src={image}
        alt=""
      />

      <div className="collection-overlay" />

      <div>

        <span>
          {subtitle}
        </span>

        <h3>
          {title}
        </h3>

        <b>
          Shop now →
        </b>

      </div>

    </button>
  );
}


/* =========================================================
   PRODUCT SKELETON
========================================================= */

function ProductSkeleton() {
  return (
    <div className="product-grid">

      {Array.from({
        length: 4
      }).map((_, index) => (

        <div
          className="skeleton-card"
          key={index}
        >

          <div className="skeleton-image" />

          <div className="skeleton-line short" />

          <div className="skeleton-line" />

          <div className="skeleton-line price" />

        </div>

      ))}

    </div>
  );
}


/* =========================================================
   CUSTOMER WORKSPACE
========================================================= */

function CustomerWorkspace({
  city,
  setCity,
  customers,
  loading,
  onSearch
}) {
  return (
    <section className="workspace">

      <div className="workspace-header">

        <div>

          <span className="eyebrow">
            CUSTOMER OPERATIONS
          </span>

          <h1>
            Customer workspace
          </h1>

          <p>
            Search customer records from
            the live GenStore database.
          </p>

        </div>

        <div className="workspace-chip">
          LIVE DATABASE
        </div>

      </div>


      <div className="customer-search-panel">

        <div>

          <span className="eyebrow">
            CUSTOMER SEARCH
          </span>

          <h2>
            Find customers by city
          </h2>

          <p>
            Search users from PostgreSQL.
            Gen-DBA observes the resulting
            SQL workload.
          </p>

        </div>


        <form
          className="customer-search-form"
          onSubmit={onSearch}
        >

          <input
            value={city}
            onChange={(event) =>
              setCity(
                event.target.value
              )
            }
            placeholder="e.g. Pune"
          />

          <button
            type="submit"
            disabled={loading}
          >
            {loading
              ? "Searching..."
              : "Search customers →"}
          </button>

        </form>

      </div>


      <div className="customer-table-card">

        <div className="section-heading">

          <div>

            <span className="eyebrow">
              RESULTS
            </span>

            <h2>
              Customer records
            </h2>

          </div>

          <span>
            {customers.length} shown
          </span>

        </div>


        {loading ? (

          <div className="customer-empty">
            Searching live customer data...
          </div>

        ) : customers.length ? (

          <div className="customer-table-wrap">

            <table>

              <thead>

                <tr>

                  <th>
                    Name
                  </th>

                  <th>
                    Email
                  </th>

                  <th>
                    City
                  </th>

                  <th>
                    Created
                  </th>

                </tr>

              </thead>


              <tbody>

                {customers.map(
                  (customer) => (

                    <tr
                      key={
                        customer.user_id
                      }
                    >

                      <td>
                        <strong>
                          {customer.name}
                        </strong>
                      </td>

                      <td>
                        {customer.email}
                      </td>

                      <td>
                        {customer.city}
                      </td>

                      <td>
                        {customer.created_at
                          ? new Date(
                              customer.created_at
                            ).toLocaleDateString()
                          : "—"}
                      </td>

                    </tr>

                  )
                )}

              </tbody>

            </table>

          </div>

        ) : (

          <div className="customer-empty">

            Search a city to pull live
            customer records.

          </div>

        )}

      </div>

    </section>
  );
}


/* =========================================================
   PRODUCT MODAL
========================================================= */

function ProductModal({
  product,
  onClose,
  onAdd
}) {
  return (
    <div
      className="modal-backdrop"
      onClick={onClose}
    >

      <div
        className="product-modal"
        onClick={(event) =>
          event.stopPropagation()
        }
      >

        <button
          className="close-button"
          onClick={onClose}
        >
          ×
        </button>


        <div className="modal-image">

          {product.image_url && (

            <img
              src={
                product.image_url
              }
              alt={
                product.name
              }
            />

          )}

        </div>


        <div className="modal-info">

          <span className="product-category">
            {product.category}
          </span>

          <h2>
            {product.name}
          </h2>


          <div className="rating-row">

            <span>
              ★
            </span>

            <b>
              {Number(
                product.rating || 4.5
              ).toFixed(1)}
            </b>

            <small>
              {product.reviews_count || 0}
              {" "}
              reviews
            </small>

          </div>


          <strong className="modal-price">
            {money(
              product.price
            )}
          </strong>


          <p>
            {product.description ||
              "A thoughtful GenStore pick for everyday use."}
          </p>


          <div className="modal-stock">

            {Number(
              product.stock
            ) > 0
              ? `In stock · ${product.stock} available`
              : "Currently out of stock"}

          </div>


          <button
            className="primary-cta"
            onClick={onAdd}
            disabled={
              Number(
                product.stock
              ) <= 0
            }
          >
            Add to cart
          </button>

        </div>

      </div>

    </div>
  );
}


/* =========================================================
   CART DRAWER
========================================================= */

function CartDrawer({
  cart,
  total,
  onClose,
  onChange,
  onCheckout
}) {
  return (
    <div
      className="drawer-backdrop"
      onClick={onClose}
    >

      <aside
        className="cart-drawer"
        onClick={(event) =>
          event.stopPropagation()
        }
      >

        <div className="drawer-head">

          <div>

            <span className="eyebrow">
              YOUR BAG
            </span>

            <h2>
              Shopping cart
            </h2>

          </div>

          <button
            className="close-button"
            onClick={onClose}
          >
            ×
          </button>

        </div>


        {cart.length ? (

          <div className="drawer-items">

            {cart.map(
              (item) => (

                <div
                  className="drawer-item"
                  key={
                    item.product_id
                  }
                >

                  <img
                    src={
                      item.image_url
                    }
                    alt=""
                  />

                  <div>

                    <strong>
                      {item.name}
                    </strong>

                    <span>
                      {money(
                        item.price
                      )}
                    </span>


                    <div className="qty-controls">

                      <button
                        onClick={() =>
                          onChange(
                            item.product_id,
                            -1
                          )
                        }
                      >
                        −
                      </button>

                      <b>
                        {item.quantity}
                      </b>

                      <button
                        onClick={() =>
                          onChange(
                            item.product_id,
                            1
                          )
                        }
                      >
                        +
                      </button>

                    </div>

                  </div>

                </div>

              )
            )}

          </div>

        ) : (

          <div className="drawer-empty">
            Your cart is waiting for something good.
          </div>

        )}


        <div className="drawer-total">

          <span>
            Subtotal
          </span>

          <strong>
            {money(total)}
          </strong>

        </div>


        <button
          className="primary-cta checkout-button"
          onClick={onCheckout}
          disabled={!cart.length}
        >
          Checkout securely →
        </button>

      </aside>

    </div>
  );
}


/* =========================================================
   CHECKOUT MODAL
========================================================= */

function CheckoutModal({
  data,
  setData,
  onClose,
  onSubmit
}) {
  return (
    <div className="modal-backdrop">

      <form
        className="checkout-modal"
        onSubmit={onSubmit}
      >

        <button
          type="button"
          className="close-button"
          onClick={onClose}
        >
          ×
        </button>


        <span className="eyebrow">
          SECURE CHECKOUT
        </span>

        <h2>
          Where should we deliver?
        </h2>

        <p>
          Use your customer details to
          complete the order.
        </p>


        <label>
          Full name

          <input
            required
            value={data.name}
            onChange={(event) =>
              setData({
                ...data,
                name:
                  event.target.value
              })
            }
          />

        </label>


        <label>
          Email

          <input
            required
            type="email"
            value={data.email}
            onChange={(event) =>
              setData({
                ...data,
                email:
                  event.target.value
              })
            }
          />

        </label>


        <label>
          City

          <input
            required
            value={data.city}
            onChange={(event) =>
              setData({
                ...data,
                city:
                  event.target.value
              })
            }
          />

        </label>


        <button
          className="primary-cta"
          type="submit"
        >
          Place order →
        </button>

      </form>

    </div>
  );
}


export default App;