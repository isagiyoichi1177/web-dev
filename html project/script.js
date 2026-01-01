document.addEventListener('DOMContentLoaded', () => {
    const cart = {
        items: [],
        total: 0
    };

    // Load persisted cart from localStorage if present
    try {
        const stored = localStorage.getItem('dc_cart');
        if (stored) {
            const parsed = JSON.parse(stored);
            if (parsed && Array.isArray(parsed.items)) {
                cart.items = parsed.items;
                cart.total = parsed.total || 0;
            }
        }
    } catch (err) {
        console.warn('Failed to load stored cart', err);
    }

    // DOM Elements
    const cartIcon = document.querySelector('.cart-icon');
    const cartCount = document.getElementById('cart-count');
    const cartSection = document.getElementById('cart');
    const cartItems = document.getElementById('cart-items');
    const totalAmount = document.getElementById('total-amount');
    const checkoutBtn = document.getElementById('checkout-btn');
    const checkoutModal = document.getElementById('checkout-modal');
    const closeModalBtn = document.querySelector('.close');
    const checkoutForm = document.getElementById('checkout-form');

    // Event Listeners
    document.querySelectorAll('.add-to-cart').forEach(button => {
        button.addEventListener('click', addToCart);
    });

    cartIcon.addEventListener('click', toggleCart);
    closeModalBtn.addEventListener('click', closeModal);
    checkoutBtn.addEventListener('click', openModal);
    checkoutForm.addEventListener('submit', handleCheckout);

    // Cart Functions
    function addToCart(e) {
        const button = e.target;
        const id = button.dataset.id;
        const name = button.dataset.name;
        const price = parseFloat(button.dataset.price);

        const existingItem = cart.items.find(item => item.id === id);
        if (existingItem) {
            existingItem.quantity++;
        } else {
            cart.items.push({ id, name, price, quantity: 1 });
        }

        updateCart();
        showNotification(`Added ${name} to cart`);
    }

    function updateCart() {
        // Update cart count
        const totalItems = cart.items.reduce((sum, item) => sum + item.quantity, 0);
        cartCount.textContent = totalItems;

        // Update cart items display
        cartItems.innerHTML = cart.items.map(item => `
            <div class="cart-item">
                <span>${item.name} x ${item.quantity}</span>
                <span>$${(item.price * item.quantity).toFixed(2)}</span>
                <button class="remove-btn" data-id="${item.id}">Remove</button>
            </div>
        `).join('');

        // Attach event listeners to remove buttons (avoid inline onclick for CSP)
        cartItems.querySelectorAll('.remove-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                removeFromCart(btn.dataset.id);
            });
        });

        // Update total
        cart.total = cart.items.reduce((sum, item) => sum + (item.price * item.quantity), 0);
        totalAmount.textContent = cart.total.toFixed(2);

        // Persist cart locally
        try {
            localStorage.setItem('dc_cart', JSON.stringify({ items: cart.items, total: cart.total }));
        } catch (err) {
            console.warn('Failed to save cart to localStorage', err);
        }

        // Try to persist cart on the server (if visitor cookie exists)
        saveCartToServer().catch(() => {
            // ignore server sync errors silently
        });
    }

    function toggleCart() {
        cartSection.classList.toggle('hidden');
    }

    function openModal() {
        if (cart.items.length === 0) {
            showNotification('Your cart is empty!');
            return;
        }
        checkoutModal.style.display = 'block';
    }

    function closeModal() {
        checkoutModal.style.display = 'none';
    }

    async function handleCheckout(e) {
        e.preventDefault();

        const formData = {
            name: document.getElementById('customer-name').value,
            email: document.getElementById('customer-email').value,
            phone: document.getElementById('customer-phone').value,
            address: document.getElementById('customer-address').value,
            items: cart.items,
            total: cart.total,
            location: null
        };

        if (document.getElementById('location-permission').checked) {
            try {
                const position = await getCurrentPosition();
                formData.location = {
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude
                };
            } catch (error) {
                console.error('Error getting location:', error);
            }
        }

        try {
            const response = await fetch('http://localhost:5000/api/orders', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });

            const data = await response.json();

            if (response.ok) {
                showNotification('Order placed successfully! (ID: ' + (data.orderId || '-') + ')');
                cart.items = [];
                updateCart();
                // hide modal consistently via class
                checkoutModal.classList.add('hidden');
                closeModal();
                checkoutForm.reset();
            } else {
                throw new Error(data.error || 'Unknown error');
            }
        } catch (error) {
            showNotification('Error placing order: ' + error.message);
        }
    }

    function getCurrentPosition() {
        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                reject(new Error('Geolocation is not supported by your browser'));
            } else {
                navigator.geolocation.getCurrentPosition(resolve, reject);
            }
        });
    }

    function showNotification(message) {
        const notification = document.createElement('div');
        notification.className = 'notification';
        notification.textContent = message;
        document.body.appendChild(notification);

        setTimeout(() => {
            notification.remove();
        }, 3000);
    }

    // Handle removing items from cart
    window.removeFromCart = function(id) {
        const index = cart.items.findIndex(item => item.id === id);
        if (index !== -1) {
            if (cart.items[index].quantity > 1) {
                cart.items[index].quantity--;
            } else {
                cart.items.splice(index, 1);
            }
            updateCart();
        }
    };

    // Save cart to server (POST /api/cart) if visitor cookie is present
    async function saveCartToServer() {
        try {
            await fetch('/api/cart', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify({ items: cart.items, total: cart.total })
            });
        } catch (err) {
            // ignore
        }
    }

    // Load cart from server and merge if visitor has server-side cart
    async function loadCartFromServer() {
        try {
            const resp = await fetch('/api/cart', { credentials: 'same-origin' });
            if (!resp.ok) return;
            const serverCart = await resp.json();
            if (serverCart && Array.isArray(serverCart.items) && serverCart.items.length > 0) {
                // prefer server cart if it's not empty
                cart.items = serverCart.items;
                cart.total = serverCart.total || 0;
                updateCart();
            }
        } catch (err) {
            // ignore network errors
        }
    }

    // Attempt to load cart from server on startup; fall back to localStorage which was loaded above
    loadCartFromServer().catch(() => {});
});