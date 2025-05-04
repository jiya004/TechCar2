import streamlit as st
import sys
import os
import pandas as pd
import sqlite3
import base64
from PIL import Image
import io
from datetime import datetime
from streamlit_lottie import st_lottie
import requests

# Add the parent directory to the Python path for utils imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import utility functions
from carzone.utils.db import (
    get_db_connection, add_seller, add_car, add_car_image, add_document,
    add_buyer_inquiry_new
)
from carzone.utils.otp_sender import send_otp, verify_otp
from carzone.utils.dropdowns import (
    models, locations, fuel_types, transmission_types,
    ownership_types, variants, extra_features,
    get_models_for_maker, get_cities_for_state
)

# Import estimation functionality
from carzone.pages.Estimate import (
    car_makes, locations as locations_estimate,
    transmission_types as transmission_types_estimate,
    calculate_depreciation, calculate_price
)

# Admin credentials
ADMIN_USERNAME = "TechCar2Admin"
ADMIN_PASSWORD = "TechCar2Admin"

# Transmission types for Estimate page
transmission_types_estimate = ['Manual', 'Automatic', 'CVT', 'DCT', 'AMT']

# Car makes and models with base prices for Estimate page
car_makes_estimate = {
    # (Include the car_makes dictionary from Estimate.py here)
    # For brevity, only a few entries shown; full list should be included in actual code
    'Maruti Suzuki': {
        'Alto K10': 3.99,
        'S-Presso': 4.25,
        'Celerio': 5.25,
        # ... add all models as in Estimate.py
    },
    'Hyundai': {
        'Grand i10 Nios': 5.73,
        'i20': 7.04,
        # ... add all models as in Estimate.py
    },
    # Add other makes similarly...
}

# Locations with multipliers for Estimate page
locations_estimate = {
    # (Include the locations dictionary from Estimate.py here)
    # For brevity, only a few entries shown; full list should be included in actual code
    'Delhi NCR': {
        'cities': ['New Delhi', 'Gurgaon', 'Noida', 'Faridabad', 'Ghaziabad'],
        'multiplier': 1.0
    },
    'Maharashtra': {
        'cities': ['Mumbai', 'Pune', 'Nagpur', 'Nashik'],
        'multiplier': 1.08
    },
    # Add other states similarly...
}

# Helper functions for Admin page
def display_image(image_data):
    if image_data:
        try:
            image = Image.open(io.BytesIO(image_data))
            st.image(image, use_column_width=True)
        except Exception as e:
            st.error(f"Error displaying image: {str(e)}")

def display_pdf(pdf_data, filename):
    if pdf_data:
        try:
            st.download_button(
                label=f"Download {filename}",
                data=pdf_data,
                file_name=filename,
                mime="application/pdf"
            )
        except Exception as e:
            st.error(f"Error displaying PDF: {str(e)}")

def admin_login():
    # Remove the Admin Login card and header, show only username, password, and login button
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login", key="admin_login_btn", help="Login as admin"):
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            st.session_state.admin_logged_in = True
            st.experimental_rerun()
        else:
            st.error("Invalid credentials")

def admin_panel():
    # Only show the main admin header/card after successful login
    if 'admin_logged_in' not in st.session_state:
        st.session_state.admin_logged_in = False
    if not st.session_state.admin_logged_in:
        # Only show the Admin Login card, not the Admin Panel card
        admin_login()
    else:
        st.markdown("""
            <div class="admin-header">
                <h1><span class="admin-emoji">🛡️</span>Admin Panel</h1>
                <p>Manage car listings and buyer inquiries</p>
            </div>
        """, unsafe_allow_html=True)

    # Get actual counts from the database
    conn = get_db_connection()
    cursor = conn.cursor()
    pending_cars_count = cursor.execute(
        "SELECT COUNT(*) FROM cars WHERE status IS NULL OR status NOT IN ('approved', 'rejected')"
    ).fetchone()[0]

    new_inquiries_count = cursor.execute(
        "SELECT COUNT(*) FROM buyer_inquiries WHERE status IS NULL OR status != 'contacted'"
    ).fetchone()[0]

    # Dashboard summary (now dynamic)
    st.markdown(f"""
        <div style="display:flex;gap:24px;margin-bottom:24px;">
            <div style="flex:1;background:#232526;padding:24px;border-radius:12px;text-align:center;">
                <span style="font-size:32px;">🚗</span>
                <h2 style="margin:8px 0 0 0;">{pending_cars_count}</h2>
                <p style="margin:0;color:#bbb;">Pending Cars</p>
            </div>
            <div style="flex:1;background:#232526;padding:24px;border-radius:12px;text-align:center;">
                <span style="font-size:32px;">📩</span>
                <h2 style="margin:8px 0 0 0;">{new_inquiries_count}</h2>
                <p style="margin:0;color:#bbb;">New Inquiries</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

    page = st.radio("Select Section", ["Car Listings", "Buyer Inquiries"], horizontal=True)
    conn = get_db_connection()
    cursor = conn.cursor()

    if page == "Car Listings":
        st.markdown("<div class='admin-card'>", unsafe_allow_html=True)
        st.header("Car Listings")
        cursor.execute("""
            SELECT 
                c.*,
                s.email as seller_email,
                s.phone as seller_phone,
                s.state as seller_state,
                s.city as seller_city,
                s.created_at as seller_created_at
            FROM cars c
            JOIN sellers s ON c.seller_id = s.id
            WHERE c.status IS NULL OR c.status NOT IN ('approved', 'rejected')
            ORDER BY c.created_at DESC
        """)
        cars = cursor.fetchall()
        if not cars:
            st.info("No car listings found.")
            st.markdown("</div>", unsafe_allow_html=True)
            return
        for car in cars:
            with st.expander(f"{car['maker']} {car['model']} - ₹{car['price']:,}"):
                st.markdown("<div class='admin-card' style='background:linear-gradient(120deg,#181818 0%,#232526 100%);'>", unsafe_allow_html=True)
                st.subheader("Car Details")
                st.write(f"**Year:** {car['year']}")
                st.write(f"**Price:** ₹{car['price']:,}")
                st.write(f"**Seller Email:** {car['seller_email']}")
                st.write(f"**Seller Phone:** {car['seller_phone']}")
                st.write(f"**Seller State:** {car['seller_state']}")
                st.write(f"**Seller City:** {car['seller_city']}")
                st.write(f"**Listed on:** {car['seller_created_at']}")

                st.subheader("Car Images")
                cursor.execute("SELECT image_data FROM car_images WHERE car_id = ?", (car['id'],))
                images = cursor.fetchall()
                if images:
                    cols = st.columns(min(4, len(images)))
                    for idx, image in enumerate(images):
                        with cols[idx % 4]:
                            display_image(image['image_data'])
                else:
                    st.info("No images uploaded")

                st.subheader("Documents")
                col1, col2 = st.columns(2)
                with col1:
                    cursor.execute("SELECT document_data FROM documents WHERE car_id = ? AND document_type = 'rc_book'", (car['id'],))
                    rc_book = cursor.fetchone()
                    if rc_book:
                        display_pdf(rc_book['document_data'], f"RC_Book_{car['id']}.pdf")
                    else:
                        st.info("RC Book not uploaded")
                with col2:
                    cursor.execute("SELECT document_data FROM documents WHERE car_id = ? AND document_type = 'insurance'", (car['id'],))
                    insurance = cursor.fetchone()
                    if insurance:
                        display_pdf(insurance['document_data'], f"Insurance_{car['id']}.pdf")
                    else:
                        st.info("Insurance document not uploaded")

                if st.button("Approve", key=f"approve_{car['id']}", help="Approve this car listing"):
                    cursor.execute("UPDATE cars SET status = 'approved' WHERE id = ?", (car['id'],))
                    conn.commit()
                    st.success("Car listing approved!")
                    st.experimental_rerun()
                if st.button("Reject", key=f"reject_{car['id']}", help="Reject this car listing"):
                    cursor.execute("UPDATE cars SET status = 'rejected' WHERE id = ?", (car['id'],))
                    conn.commit()
                    st.success("Car listing rejected!")
                    st.experimental_rerun()
                st.markdown("</div>", unsafe_allow_html=True)

    elif page == "Buyer Inquiries":
        st.markdown("<div class='admin-card'>", unsafe_allow_html=True)
        st.header("Buyer Inquiries")
        cursor.execute("""
            SELECT 
                bi.*,
                c.maker,
                c.model,
                c.price,
                s.email as seller_email
            FROM buyer_inquiries bi
            JOIN cars c ON bi.car_id = c.id
            JOIN sellers s ON c.seller_id = s.id
            ORDER BY bi.created_at DESC
        """)
        inquiries = cursor.fetchall()
        if not inquiries:
            st.info("No buyer inquiries found.")
            st.markdown("</div>", unsafe_allow_html=True)
            return
        for inquiry in inquiries:
            with st.expander(f"Inquiry for {inquiry['maker']} {inquiry['model']} - {inquiry['created_at']}"):
                st.markdown("<div class='admin-card' style='background:linear-gradient(120deg,#181818 0%,#232526 100%);'>", unsafe_allow_html=True)
                st.write(f"**Buyer Name:** {inquiry['name']}")
                st.write(f"**Buyer Email:** {inquiry['email']}")
                st.write(f"**Buyer Phone:** {inquiry['phone']}")
                st.write(f"**Message:** {inquiry['message']}")
                st.write(f"**Car Price:** ₹{inquiry['price']:,}")
                st.write(f"**Seller Email:** {inquiry['seller_email']}")
                if st.button("Mark as Contacted", key=f"contacted_{inquiry['id']}", help="Mark this inquiry as contacted"):
                    cursor.execute("UPDATE buyer_inquiries SET status = 'contacted' WHERE id = ?", (inquiry['id'],))
                    conn.commit()
                    st.success("Marked as contacted!")
                    st.experimental_rerun()
                st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

def get_car_listings(filters=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        SELECT 
            c.*,
            s.email as seller_email,
            s.phone as seller_phone,
            s.state as seller_state,
            s.city as seller_city,
            ci.image_data as image_data
        FROM cars c
        JOIN sellers s ON c.seller_id = s.id
        LEFT JOIN car_images ci ON c.id = ci.car_id
        WHERE c.status = 'approved'
    """
    params = []
    if filters:
        conditions = []
        if filters.get('maker'):
            conditions.append("c.maker = ?")
            params.append(filters['maker'])
        if filters.get('model'):
            conditions.append("c.model = ?")
            params.append(filters['model'])
        if filters.get('fuel_type'):
            conditions.append("c.fuel_type = ?")
            params.append(filters['fuel_type'])
        if filters.get('transmission'):
            conditions.append("c.transmission = ?")
            params.append(filters['transmission'])
        if filters.get('min_price'):
            conditions.append("c.price >= ?")
            params.append(filters['min_price'])
        if filters.get('max_price'):
            conditions.append("c.price <= ?")
            params.append(filters['max_price'])
        if filters.get('state'):
            conditions.append("c.state = ?")
            params.append(filters['state'])
        if filters.get('city'):
            conditions.append("c.city = ?")
            params.append(filters['city'])
        if conditions:
            query += " AND " + " AND ".join(conditions)
    query += " ORDER BY c.created_at DESC"
    cursor.execute(query, params)
    cars = cursor.fetchall()
    car_dict = {}
    for car in cars:
        car_id = car['id']
        if car_id not in car_dict:
            car_dict[car_id] = dict(car)
            car_dict[car_id]['images'] = []
        if car['image_data']:
            car_dict[car_id]['images'].append(car['image_data'])
    conn.close()
    return list(car_dict.values())

def main():
    st.set_page_config(page_title="TechCar2 - Used Car Hub", page_icon="🚗", layout="wide")

    st.markdown("""
        <style>
        body::before {
            content: "TechCar2";
            position: fixed;
            top: 50%;
            left: 50%;
            font-size: 7vw;
            color: rgba(25, 118, 210, 0.08); /* blue tint */
            z-index: 9999;
            pointer-events: none;
            transform: translate(-50%, -50%) rotate(-25deg);
            user-select: none;
            font-weight: 900;
            letter-spacing: 2vw;
        }
        .main-header, .section-header, .admin-header, .sell-header, .estimate-header {
            background: linear-gradient(90deg, #1976d2 0%, #8e0545 100%);
            color: #fff;
            padding: 32px 24px 24px 24px;
            border-radius: 18px;
            margin-bottom: 32px;
            box-shadow: 0 6px 32px rgba(25, 118, 210, 0.18);
            font-size: 2.5rem;
            font-weight: 800;
            letter-spacing: 2px;
            text-align: center;
        }
        .admin-card, .sell-card, .estimate-card, .custom-card {
            background: linear-gradient(90deg, #1976d2 0%, #8e0545 100%);
            border-radius: 18px;
            box-shadow: 0 4px 24px rgba(142, 5, 69, 0.18);
            padding: 32px 24px;
            margin-bottom: 32px;
            color: #fff;
            transition: box-shadow 0.3s, transform 0.3s;
        }
        .section-gradient {
            background: linear-gradient(90deg, #1976d2 0%, #8e0545 100%);
            border-radius: 18px;
            box-shadow: 0 4px 24px rgba(142, 5, 69, 0.18);
            padding: 32px 24px;
            margin-bottom: 32px;
            color: #fff;
        }
        .admin-card:hover, .sell-card:hover, .estimate-card:hover, .custom-card:hover {
            box-shadow: 0 8px 32px #8e054555;
            transform: translateY(-2px) scale(1.01);
        }
        .custom-btn, button[data-testid="baseButton"], .stButton > button {
            background: linear-gradient(90deg, #1976d2 0%, #8e0545 100%) !important;
            color: #fff !important;
            font-size: 18px !important;
            font-weight: 700 !important;
            border-radius: 12px !important;
            border: none !important;
            padding: 12px 32px !important;
            margin: 8px 0 !important;
            box-shadow: 0 2px 8px #8e054555 !important;
            transition: background 0.3s, color 0.3s, box-shadow 0.3s, transform 0.2s !important;
            cursor: pointer !important;
        }
        .custom-btn:hover, button[data-testid="baseButton"]:hover, .stButton > button:hover {
            background: linear-gradient(90deg, #8e0545 0%, #1976d2 100%) !important;
            color: #fff !important;
            box-shadow: 0 4px 16px #1976d255 !important;
            transform: scale(1.04) !important;
        }
        .feature-badge {
            display: inline-block;
            background: linear-gradient(90deg, #8e0545 0%, #1976d2 100%);
            color: #fff;
            font-size: 16px;
            font-weight: 700;
            border-radius: 10px;
            padding: 6px 18px;
            margin: 4px 6px 4px 0;
            box-shadow: 0 2px 8px #8e054555;
            letter-spacing: 1px;
        }
        .nav-header {
            background: linear-gradient(120deg, #1976d2 0%, #8e0545 100%);
            padding: 18px 0 10px 0;
            border-radius: 0 0 18px 18px;
            box-shadow: 0 2px 12px rgba(25, 118, 210, 0.12);
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 32px;
            margin-bottom: 32px;
        }
        .nav-link {
            color: #fff;
            font-size: 20px;
            font-weight: 700;
            text-decoration: none;
            padding: 8px 22px;
            border-radius: 8px;
            transition: background 0.2s, color 0.2s;
        }
        .nav-link.selected, .nav-link:hover {
            background: linear-gradient(90deg, #8e0545 0%, #1976d2 100%);
            color: #fff !important;
            text-shadow: none;
        }
        /* Inputs and expander styling */
        .stTextInput > div > input, .stNumberInput > div > input, .stSelectbox > div > div {
            background: #232526 !important;
            color: #fff !important;
            border-radius: 8px !important;
            border: 1.5px solid #1976d2 !important;
        }
        .stExpander > div {
            background: linear-gradient(90deg, #1976d2 0%, #8e0545 100%);
            color: #fff !important;
            border-radius: 12px !important;
            border: 1.5px solid #8e0545 !important;
        }
        /* Scrollbar styling */
        ::-webkit-scrollbar {
            width: 10px;
            background: #232526;
        }
        ::-webkit-scrollbar-thumb {
            background: linear-gradient(90deg, #1976d2 0%, #8e0545 100%);
            border-radius: 8px;
        }
        </style>
    """, unsafe_allow_html=True)

    # Place this at the top of your main() function, before any page logic

    st.markdown("""
        <style>
        .nav-header {
            background: linear-gradient(120deg, #232526 0%, #414345 100%);
            padding: 18px 0 10px 0;
            border-radius: 0 0 18px 18px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.12);
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 32px;
            margin-bottom: 32px;
        }
        .nav-link {
            color: #fff;
            font-size: 20px;
            font-weight: 700;
            text-decoration: none;
            padding: 8px 22px;
            border-radius: 8px;
            transition: background 0.2s, color 0.2s;
        }
        .nav-link.selected, .nav-link:hover {
            background: linear-gradient(90deg, #43e97b 0%, #38f9d7 100%);
            color: #232526 !important;
            text-shadow: none;
        }
        </style>
    """, unsafe_allow_html=True)

    # Navigation logic
    PAGES = ["Home", "Buy", "Sell", "Estimate", "Admin"]
    if "nav_page" not in st.session_state:
        st.session_state["nav_page"] = "Home"

    nav_cols = st.columns(len(PAGES))
    for i, page in enumerate(PAGES):
        if nav_cols[i].button(page, key=f"nav_{page}"):
            st.session_state["nav_page"] = page

    page = st.session_state["nav_page"]

    # Now use `page` variable for your section logic
    if page == "Home":
        st.markdown("""
            <div class="section-header">🚗 Welcome to TechCar2</div>
        """, unsafe_allow_html=True)
        st.write("Navigate above to buy, sell, estimate prices, or manage admin tasks.")

    elif page == "Buy":
        st.markdown("""
            <div class="estimate-header">
                <h1><span class="buy-emoji">🚗</span>Find Your Perfect Car</h1>
                <p>Browse through our extensive collection of verified cars</p>
            </div>
        """, unsafe_allow_html=True)
        # Initialize session state variables
        if 'selected_car' not in st.session_state:
            st.session_state.selected_car = None
        if 'otp_verified' not in st.session_state:
            st.session_state.otp_verified = False
        if 'email' not in st.session_state:
            st.session_state.email = None
        if 'show_contact' not in st.session_state:
            st.session_state.show_contact = False
        if 'current_image_index' not in st.session_state:
            st.session_state.current_image_index = 0

        # Filters in a collapsible section
        with st.expander("🔍 Advanced Filters", expanded=True):
            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown("### 🚗 Car Details")
                maker = st.selectbox("Car Maker", [""] + list(models.keys()))
                if maker:
                    model = st.selectbox("Car Model", [""] + get_models_for_maker(maker))
                else:
                    model = ""
                fuel_type = st.selectbox("Fuel Type", [""] + fuel_types)

            with col2:
                st.markdown("### 💰 Price Range")
                min_price = st.number_input("Min Price (₹)", min_value=0, value=0, step=100000)
                max_price = st.number_input("Max Price (₹)", min_value=0, value=10000000, step=100000)
                transmission = st.selectbox("Transmission", [""] + transmission_types)

            with col3:
                st.markdown("### 📍 Location")
                state = st.selectbox("State", [""] + list(locations.keys()))
                if state:
                    city = st.selectbox("City", [""] + get_cities_for_state(state))
                else:
                    city = ""

        # Apply filters
        filters = {
            'maker': maker if maker else None,
            'model': model if model else None,
            'fuel_type': fuel_type if fuel_type else None,
            'transmission': transmission if transmission else None,
            'min_price': min_price if min_price > 0 else None,
            'max_price': max_price if max_price < 10000000 else None,
            'state': state if state else None,
            'city': city if city else None
        }

        # Get and display car listings
        cars = get_car_listings(filters)

        if not cars:
            st.info("No cars found matching your criteria.")
        else:
            st.markdown(f"### 🚗 Found {len(cars)} Cars")

            card_cols = st.columns(min(len(cars), 4))  # Show up to 4 cards per row
            for idx, car in enumerate(cars):
                with card_cols[idx % 4]:
                    img_key = f"img_idx_{car['id']}"
                    details_key = f"details_{car['id']}"
                    contact_key = f"contact_{car['id']}"
                    if img_key not in st.session_state:
                        st.session_state[img_key] = 0
                    if details_key not in st.session_state:
                        st.session_state[details_key] = False
                    if contact_key not in st.session_state:
                        st.session_state[contact_key] = False

                    st.markdown("<div style='background: #232323; border-radius: 12px; padding: 18px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.15);'>", unsafe_allow_html=True)

                    images = car.get('images', [])
                    if images:
                        img_idx = st.session_state[img_key]
                        img = images[img_idx]
                        st.image(Image.open(io.BytesIO(img)), use_column_width=True)
                        col_img1, col_img2, col_img3 = st.columns([1,2,1])
                        with col_img1:
                            if st.button("❮", key=f"prev_{car['id']}"):
                                st.session_state[img_key] = (img_idx - 1) % len(images)
                        with col_img3:
                            if st.button("❯", key=f"next_{car['id']}"):
                                st.session_state[img_key] = (img_idx + 1) % len(images)
                    else:
                        st.image("https://via.placeholder.com/350x200?text=No+Image", use_column_width=True)

                    st.markdown(f"""
                        <h3 style='color:white;margin:10px 0 0 0;'>{car['maker']} {car['model']}</h3>
                        <div style='color:#4CAF50;font-size:22px;font-weight:700;margin-bottom:8px;'>₹{car['price']:,}</div>
                    """, unsafe_allow_html=True)

                    st.markdown(f"""
                        <div style='color:#bbb;font-size:15px;margin-bottom:8px;'>
                            <b>{car['year']}</b> • <b>{car['km_driven']:,} km</b> • <b>{car['fuel_type']}</b> • <b>{car['transmission']}</b>
                        </div>
                    """, unsafe_allow_html=True)

                    if st.button("Show Less" if st.session_state[details_key] else "More Details", key=f"details_btn_{car['id']}"):
                        st.session_state[details_key] = not st.session_state[details_key]
                    if st.session_state[details_key]:
                        st.markdown("<div style='background:#181818;padding:10px 12px;border-radius:8px;margin:10px 0;color:#eee;'>", unsafe_allow_html=True)
                        st.write(f"**Variant:** {car['variant']}")
                        st.write(f"**Ownership:** {car['ownership']}")
                        st.write(f"**Location:** {car['city']}, {car['state']}")
                        if car.get('extra_features'):
                            st.write("**Features:**")
                            for feature in car['extra_features'].split(','):
                                st.markdown(f"<span class='feature-badge'>{feature.strip()}</span>", unsafe_allow_html=True)
                        st.markdown("</div>", unsafe_allow_html=True)

                    if st.button("Contact Seller", key=f"contact_btn_{car['id']}"):
                        st.session_state[contact_key] = True
                    if st.session_state[contact_key]:
                        st.markdown("<div style='background:#181818;padding:16px 12px;border-radius:8px;margin:10px 0;color:#eee;'>", unsafe_allow_html=True)
                        st.write("**Contact Seller**")
                        email = st.text_input("Enter your email address", key=f"email_{car['id']}")
                        if st.button("Send OTP", key=f"send_otp_{car['id']}"):
                            if email:
                                success, message = send_otp(email)
                                if success:
                                    st.success(message)
                                    st.session_state[f"otp_email_{car['id']}"] = email
                                else:
                                    st.error(message)
                            else:
                                st.error("Please enter your email address")
                        otp_input = st.text_input("Enter OTP", key=f"otp_{car['id']}")
                        if st.button("Verify OTP", key=f"verify_otp_{car['id']}"):
                            if otp_input and st.session_state.get(f"otp_email_{car['id']}"):
                                success, message = verify_otp(st.session_state[f"otp_email_{car['id']}"] , otp_input)
                                if success:
                                    st.success(message)
                                    st.write(f"Seller's Phone: **{car['seller_phone']}**")
                                else:
                                    st.error(message)
                            else:
                                st.error("Please enter both email and OTP")
                        if st.button("Close", key=f"close_contact_{car['id']}"):
                            st.session_state[contact_key] = False
                        st.markdown("</div>", unsafe_allow_html=True)

                    st.markdown("</div>", unsafe_allow_html=True)

    elif page == "Sell":
        st.markdown("""
            <div class="estimate-header">
                <h1><span class="sell-emoji">🚙</span>Sell Your Car</h1>
                <p>List your car in minutes and reach thousands of buyers!</p>
            </div>
        """, unsafe_allow_html=True)
        # Initialize session state for OTP verification and email
        if 'otp_verified_sell' not in st.session_state:
            st.session_state.otp_verified_sell = False
        if 'email_sell' not in st.session_state:
            st.session_state.email_sell = None

        st.markdown("""
            <style>
            .sell-header {
                background: linear-gradient(120deg, #232526 0%, #393939 100%);
                color: white;
                padding: 32px 24px 24px 24px;
                border-radius: 18px;
                margin-bottom: 32px;
                box-shadow: 0 6px 32px rgba(0,0,0,0.25);
                position: relative;
                overflow: hidden;
            }
            .sell-header h1 {
                font-size: 44px;
                font-weight: 800;
                margin: 0 0 8px 0;
                letter-spacing: 2px;
                display: flex;
                align-items: center;
            }
            .sell-header .car-emoji {
                font-size: 48px;
                margin-right: 18px;
                filter: drop-shadow(0 2px 8px #0008);
            }
            .sell-header p {
                font-size: 20px;
                opacity: 0.92;
                margin: 0;
            }
            .sell-header::before {
                content: '';
                position: absolute;
                top: -60px; left: -60px;
                width: 200px; height: 200px;
                background: radial-gradient(circle, #2196F3 0%, transparent 70%);
                opacity: 0.18;
                animation: shine 4s linear infinite;
            }
            @keyframes shine {
                0% { left: -60px; top: -60px; }
                100% { left: 80vw; top: 60px; }
            }
            .sell-card {
                background: linear-gradient(120deg, #232526 0%, #393939 100%);
                border-radius: 16px;
                box-shadow: 0 2px 16px rgba(0,0,0,0.18);
                padding: 32px 24px;
                margin-bottom: 32px;
                color: white;
                transition: box-shadow 0.3s, transform 0.3s;
            }
            .sell-card:hover {
                box-shadow: 0 8px 32px rgba(33,150,243,0.18);
                transform: translateY(-2px) scale(1.01);
            }
            .sell-btn {
                width: 100%;
                padding: 16px;
                font-size: 20px;
                font-weight: 700;
                border-radius: 12px;
                border: none;
                background: linear-gradient(90deg, #2196F3 0%, #38f9d7 100%);
                color: #232323;
                margin-top: 18px;
                margin-bottom: 8px;
                box-shadow: 0 2px 8px #38f9d755;
                transition: background 0.3s, color 0.3s, box-shadow 0.3s, transform 0.2s;
                cursor: pointer;
            }
            .sell-btn:hover {
                background: linear-gradient(90deg, #38f9d7 0%, #2196F3 100%);
                color: #111;
                box-shadow: 0 4px 16px #2196F355;
                transform: scale(1.04);
            }
            .sell-feature-tag {
                background: linear-gradient(90deg, #43e97b 0%, #38f9d7 100%);
                color: #232323;
                padding: 6px 16px;
                border-radius: 15px;
                font-size: 15px;
                margin: 4px 6px 4px 0;
                display: inline-block;
                font-weight: 500;
                box-shadow: 0 1px 4px #38f9d755;
                transition: background 0.3s;
            }
            .sell-feature-tag:hover {
                background: linear-gradient(90deg, #38f9d7 0%, #43e97b 100%);
            }
            </style>
        """, unsafe_allow_html=True)

        # Step 1: Email OTP Verification
        if not st.session_state.otp_verified_sell:
            st.markdown("<div class='sell-card'>", unsafe_allow_html=True)
            st.subheader("Step 1: Email Verification")
            email = st.text_input("Enter your email address", key="sell_email")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Send OTP", key="send_otp_sell_btn", help="Send OTP to your email"):
                    if email:
                        success, message = send_otp(email)
                        if success:
                            st.success(message)
                            st.session_state.email_sell = email
                        else:
                            st.error(message)
                    else:
                        st.error("Please enter your email address")
            with col2:
                otp_input = st.text_input("Enter OTP", key="sell_otp_input")
                if st.button("Verify OTP", key="verify_otp_sell_btn", help="Verify the OTP sent to your email"):
                    if otp_input and st.session_state.email_sell:
                        success, message = verify_otp(st.session_state.email_sell, otp_input)
                        if success:
                            st.success(message)
                            st.session_state.otp_verified_sell = True
                        else:
                            st.error(message)
                    else:
                        st.error("Please enter both email and OTP")
            st.markdown("</div>", unsafe_allow_html=True)

        # Step 2: Car Details Form
        if st.session_state.otp_verified_sell:
            st.markdown("<div class='sell-card'>", unsafe_allow_html=True)
            st.subheader("Step 2: Car Details")
            with st.form("car_details_form"):
                col1, col2 = st.columns(2)
                with col1:
                    maker = st.selectbox("Car Maker", list(models.keys()))
                with col2:
                    model = st.selectbox("Car Model", get_models_for_maker(maker))
                col1, col2 = st.columns(2)
                with col1:
                    fuel_type = st.selectbox("Fuel Type", fuel_types)
                with col2:
                    transmission = st.selectbox("Transmission", transmission_types)
                col1, col2 = st.columns(2)
                with col1:
                    variant = st.selectbox("Variant", variants)
                with col2:
                    ownership = st.selectbox("Ownership", ownership_types)
                col1, col2 = st.columns(2)
                with col1:
                    year = st.number_input("Year of Manufacture", min_value=1990, max_value=2024, value=2020)
                with col2:
                    km_driven = st.number_input("Kilometers Driven", min_value=0, value=10000)
                col1, col2 = st.columns(2)
                with col1:
                    mileage = st.number_input("Mileage (km/l)", min_value=0.0, value=20.0)
                with col2:
                    price = st.number_input("Expected Price (₹)", min_value=0, value=500000)
                col1, col2 = st.columns(2)
                with col1:
                    state = st.selectbox("State", list(locations.keys()))
                with col2:
                    city = st.selectbox("City", get_cities_for_state(state))
                phone = st.text_input("Contact Number")
                contact_time = st.text_input("Preferred Contact Time (e.g., 10 AM - 6 PM)")
                selected_features = st.multiselect("Extra Features", extra_features)
                st.markdown("<div style='margin-bottom:10px;'></div>", unsafe_allow_html=True)
                st.markdown("<div>", unsafe_allow_html=True)
                for feature in selected_features:
                    st.markdown(f"<span class='sell-feature-tag'>{feature}</span>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
                st.subheader("Upload Images")
                car_images = st.file_uploader(
                    "Upload Car Images (up to 8)",
                    type=['jpg', 'jpeg', 'png'],
                    accept_multiple_files=True
                )
                st.subheader("Upload Documents")
                rc_book = st.file_uploader("Upload RC Book", type=['pdf'])
                insurance = st.file_uploader("Upload Insurance Document", type=['pdf'])
                submitted = st.form_submit_button("Submit Car Details", help="Submit your car for listing")
                if submitted:
                    if len(car_images) > 8:
                        st.error("Maximum 8 car images allowed")
                    elif not car_images:
                        st.error("Please upload at least one car image")
                    elif not rc_book:
                        st.error("Please upload RC Book")
                    elif not insurance:
                        st.error("Please upload Insurance Document")
                    else:
                        seller_id = add_seller(
                            st.session_state.email_sell,
                            phone,
                            state,
                            city
                        )
                        if seller_id:
                            car_data = {
                                'maker': maker,
                                'model': model,
                                'fuel_type': fuel_type,
                                'transmission': transmission,
                                'variant': variant,
                                'year': year,
                                'km_driven': km_driven,
                                'mileage': mileage,
                                'ownership': ownership,
                                'price': price,
                                'state': state,
                                'city': city,
                                'extra_features': selected_features
                            }
                            car_id = add_car(seller_id, car_data)
                            if car_id:
                                for image in car_images:
                                    image_bytes = image.getvalue()
                                    add_car_image(car_id, image_bytes)
                                rc_book_bytes = rc_book.getvalue()
                                add_document(car_id, 'rc_book', rc_book_bytes)
                                insurance_bytes = insurance.getvalue()
                                add_document(car_id, 'insurance', insurance_bytes)
                                st.success("Car submitted successfully! After admin verification, it will be listed within 24 hours.")
                                st.session_state.otp_verified_sell = False
                                st.session_state.email_sell = None
                            else:
                                st.error("Error saving car details. Please try again.")
                        else:
                            st.error("Error saving seller details. Please try again.")
            st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    elif page == "Estimate":
        st.markdown("""
            <div class="estimate-header">
                <h1><span class="money-emoji">💰</span>Car Price Estimator</h1>
                <p>Get an instant, market-based price estimate for your car</p>
            </div>
        """, unsafe_allow_html=True)

        with st.form("estimate_form"):
            col1, col2 = st.columns(2)
            with col1:
                maker = st.selectbox("Car Maker", list(car_makes.keys()))
            with col2:
                model_name = st.selectbox("Car Model", list(car_makes[maker].keys()))
            col1, col2 = st.columns(2)
            with col1:
                year = st.number_input("Year of Manufacture", min_value=1990, max_value=datetime.now().year, value=2020)
            with col2:
                km_driven = st.number_input("Kilometers Driven", min_value=0, value=10000)
            col1, col2 = st.columns(2)
            with col1:
                fuel_type = st.selectbox("Fuel Type", fuel_types)
            with col2:
                transmission = st.selectbox("Transmission", transmission_types_estimate)
            col1, col2 = st.columns(2)
            with col1:
                condition = st.selectbox("Condition", ['Excellent', 'Good', 'Fair', 'Poor'])
            with col2:
                body_style = st.selectbox("Body Style", ['Sedan', 'Hatchback', 'Wagon', 'Hardtop', 'Convertible', 'SUV', 'MPV', 'Truck', 'Van', 'Bus', 'Mini', 'Other'])
            col1, col2 = st.columns(2)
            with col1:
                drive_wheels = st.selectbox("Drive Wheels", ['FWD', 'RWD', '4WD'])
            with col2:
                previous_owners = st.selectbox("Previous Owners", ['First Owner', 'Second Owner', 'Third Owner', 'Fourth Owner', 'Fifth Owner or More'])
            state = st.selectbox("State", list(locations_estimate.keys()))
            city = st.selectbox("City", locations_estimate[state]['cities'])
            submitted = st.form_submit_button("Estimate Price")

        if submitted:
            base_price = car_makes[maker][model_name] * 100000  # Convert lakhs to rupees
            estimated_price = calculate_price(
                base_price, year, fuel_type, transmission, km_driven, condition,
                body_style, drive_wheels, state, city, previous_owners
            )
            st.success(f"Estimated Price: ₹{estimated_price:,.0f}")

    elif page == "Admin":
        st.markdown("""
            <div class="estimate-header">
                <h1><span class="admin-emoji">🛡️</span>Admin Panel</h1>
                <p>Manage car listings and buyer inquiries</p>
            </div>
        """, unsafe_allow_html=True)
        if 'admin_logged_in' not in st.session_state:
            st.session_state.admin_logged_in = False
        if not st.session_state.admin_logged_in:
            admin_login()
        else:
            admin_panel()

if __name__ == "__main__":
    main()
