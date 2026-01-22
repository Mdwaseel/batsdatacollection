import streamlit as st
import json
from datetime import datetime
import pandas as pd
from io import BytesIO
from supabase import create_client, Client
from PIL import Image
import os
from dotenv import load_dotenv
import uuid

import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configure page
st.set_page_config(
    page_title="Product Data Collection",
    page_icon="🛍️",
    layout="wide"
)

# ============================================
# SUPABASE CONFIGURATION
# ============================================

# Direct Supabase initialization (no caching)
def init_supabase():
    """Initialize Supabase client"""
    # Try to get from Streamlit secrets first, then environment variables
    url = st.secrets.get("SUPABASE_URL", os.getenv("SUPABASE_URL", ""))
    key = st.secrets.get("SUPABASE_KEY", os.getenv("SUPABASE_KEY", ""))
    
    if not url or not key:
        st.error("⚠️ Supabase credentials not configured!")
        st.stop()
    
    return create_client(url, key)

try:
    supabase: Client = init_supabase()
    SUPABASE_CONNECTED = True
except Exception as e:
    st.error(f"Failed to connect to Supabase: {e}")
    SUPABASE_CONNECTED = False

def validate_image(file):
    """Validate uploaded image"""
    if file is None:
        return True
    
    # Check file size (max 5MB)
    if file.size > 5 * 1024 * 1024:
        st.warning(f"⚠️ {file.name} is too large (max 5MB). Image skipped.")
        return False
    
    # Check file type
    allowed_types = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp']
    if file.type not in allowed_types:
        st.warning(f"⚠️ {file.name} has invalid type. Only PNG/JPG/WEBP allowed.")
        return False
    
    return True

def compress_image(file, max_size_mb=1):
    """Compress image if larger than max_size_mb"""
    if file is None or file.size <= max_size_mb * 1024 * 1024:
        return file
    
    try:
        img = Image.open(file)
        
        # Convert to RGB if needed
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        # Compress
        output = BytesIO()
        quality = 85
        img.save(output, format='JPEG', quality=quality, optimize=True)
        output.seek(0)
        
        # Create new file-like object
        output.name = file.name.rsplit('.', 1)[0] + '.jpg'
        output.type = 'image/jpeg'
        
        st.info(f"✅ Compressed {file.name} from {file.size/1024:.0f}KB to {output.getbuffer().nbytes/1024:.0f}KB")
        return output
    except Exception as e:
        logger.error(f"Error compressing image: {e}")
        return file

# ============================================
# SUPABASE FUNCTIONS
# ============================================

def upload_image_to_supabase(file, folder="products"):
    """Upload image to Supabase Storage"""
    if file is None:
        return None
    
    # Validate image
    if not validate_image(file):
        return None
    
    # Compress image
    file = compress_image(file)
    
    try:
        # Generate unique filename
        file_ext = file.name.split('.')[-1]
        unique_name = f"{folder}/{uuid.uuid4()}.{file_ext}"
        
        # Upload to Supabase Storage
        file_bytes = file.read()
        file.seek(0)  # Reset file pointer
        
        result = supabase.storage.from_('product-images').upload(
            unique_name,
            file_bytes,
            {
                "content-type": file.type,
                "x-upsert": "true"
            }
        )
        
        # Get public URL
        public_url = supabase.storage.from_('product-images').get_public_url(unique_name)
        
        logger.info(f"Image uploaded successfully: {unique_name}")
        
        return {
            'filename': file.name,
            'path': unique_name,
            'url': public_url
        }
    
    except Exception as e:
        logger.error(f"Error uploading image: {e}")
        st.error(f"Error uploading {file.name}: {str(e)[:100]}")
        return None

def save_product_to_supabase(product_data):
    """Save product to Supabase database"""
    try:
        # Insert into products table
        result = supabase.table('products').insert(product_data).execute()
        logger.info(f"Product saved: {product_data.get('product_name')}")
        return result.data[0] if result.data else None
    
    except Exception as e:
        logger.error(f"Error saving product: {e}")
        st.error(f"Error saving product: {str(e)[:200]}")
        return None

def get_all_products_from_supabase():
    """Fetch all products from Supabase"""
    try:
        result = supabase.table('products').select("*").order('created_at', desc=True).execute()
        logger.info(f"Fetched {len(result.data)} products from database")
        return result.data
    
    except Exception as e:
        logger.error(f"Error fetching products: {e}")
        st.error(f"Error fetching products: {str(e)[:100]}")
        return []

def delete_product_from_supabase(product_id):
    """Delete product from Supabase"""
    try:
        # Delete product
        supabase.table('products').delete().eq('id', product_id).execute()
        logger.info(f"Product deleted: {product_id}")
        return True
    
    except Exception as e:
        logger.error(f"Error deleting product: {e}")
        st.error(f"Error deleting product: {str(e)[:100]}")
        return False

def search_products(query):
    """Search products by name or SKU"""
    try:
        result = supabase.table('products').select("*").or_(
            f"product_name.ilike.%{query}%,sku.ilike.%{query}%"
        ).execute()
        logger.info(f"Search for '{query}' returned {len(result.data)} results")
        return result.data
    
    except Exception as e:
        logger.error(f"Error searching products: {e}")
        st.error(f"Error searching products: {str(e)[:100]}")
        return []

# ============================================
# CUSTOM CSS
# ============================================

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 2rem;
    }
    .section-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        margin: 1.5rem 0 1rem 0;
        font-weight: 600;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    .info-box {
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    .metric-card {
        background: white;
        border-radius: 10px;
        padding: 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        text-align: center;
    }
    .metric-value {
        font-size: 2.5rem;
        font-weight: bold;
        color: #667eea;
    }
    .metric-label {
        color: #666;
        font-size: 0.9rem;
        margin-top: 0.5rem;
    }
    .product-card {
        background: white;
        border-radius: 10px;
        padding: 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
        border-left: 4px solid #667eea;
    }
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .status-connected {
        background: #d4edda;
        color: #155724;
    }
    .status-disconnected {
        background: #f8d7da;
        color: #721c24;
    }
</style>
""", unsafe_allow_html=True)

# ============================================
# HEADER & SIDEBAR
# ============================================

st.markdown('<div class="main-header">🏏 Product Data Collection System</div>', unsafe_allow_html=True)

# Connection status
if SUPABASE_CONNECTED:
    st.success("✅ Connected to Database")
else:
    st.error("❌ Not connected to Supabase. Check your credentials.")

with st.sidebar:
    st.image("https://via.placeholder.com/200x80/667eea/ffffff?text=Your+Logo", width=200)
    st.markdown("---")
    
    # Database status
    if SUPABASE_CONNECTED:
        st.markdown('<span class="status-badge status-connected">🟢 Database Online</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-badge status-disconnected">🔴 Database Offline</span>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    page = st.radio(
        "Navigation",
        ["➕ Add New Product", "📋 View All Products", "🔍 Search Products", "📊 Export Data", "⚙️ Database Setup"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    
    # Get product count
    if SUPABASE_CONNECTED:
        try:
            products = get_all_products_from_supabase()
            product_count = len(products)
        except:
            product_count = 0
    else:
        product_count = 0
    
    st.markdown(f"**Total Products:** {product_count}")
    if st.button("🔄 Refresh", key="refresh_count", use_container_width=True):
        st.rerun()

# ============================================
# PAGE 0: DATABASE SETUP
# ============================================

if page == "⚙️ Database Setup":
    st.markdown('<div class="section-header">⚙️ Database Setup Guide</div>', unsafe_allow_html=True)
    
    st.markdown("""
    ### 📚 Step-by-Step Supabase Setup
    
    #### 1️⃣ Create Supabase Account
    - Go to [supabase.com](https://supabase.com)
    - Sign up for a free account
    - Create a new project
    
    #### 2️⃣ Get Your Credentials
    - Go to Project Settings → API
    - Copy **Project URL** and **anon public** key
    
    #### 3️⃣ Create Database Table
    Run this SQL in Supabase SQL Editor:
    """)
    
    sql_code = """
-- Create products table
CREATE TABLE products (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Basic Info
    product_name TEXT NOT NULL,
    product_type TEXT NOT NULL,
    sku TEXT,
    regular_price DECIMAL(10,2) NOT NULL,
    sale_price DECIMAL(10,2),
    stock_status TEXT,
    stock_quantity INTEGER,
    weight DECIMAL(10,2),
    category TEXT,
    short_description TEXT,
    full_description TEXT,
    
    -- Images
    main_image JSONB,
    gallery_images JSONB,
    
    -- Variations (for variable products)
    variations JSONB,
    
    -- Deep Customization (for bats)
    deep_customization JSONB,
    
    -- Full product data (complete JSON)
    product_data JSONB
);

-- Create storage bucket for images
INSERT INTO storage.buckets (id, name, public)
VALUES ('product-images', 'product-images', true);

-- Allow public access to images
CREATE POLICY "Public Access"
ON storage.objects FOR SELECT
USING ( bucket_id = 'product-images' );

-- Allow authenticated uploads
CREATE POLICY "Authenticated Upload"
ON storage.objects FOR INSERT
WITH CHECK ( bucket_id = 'product-images' );

-- Create indexes for better performance
CREATE INDEX idx_products_name ON products(product_name);
CREATE INDEX idx_products_sku ON products(sku);
CREATE INDEX idx_products_type ON products(product_type);
CREATE INDEX idx_products_created ON products(created_at);
"""
    
    st.code(sql_code, language="sql")
    
    st.markdown("""
    #### 4️⃣ Configure Streamlit
    
    **Option A: Using .env file (Local Development)**
    Create a `.env` file in your project folder:
    ```
    SUPABASE_URL=your-project-url-here
    SUPABASE_KEY=your-anon-key-here
    ```
    
    **Option B: Using Streamlit Secrets (Cloud Deployment)**
    Create `.streamlit/secrets.toml`:
    ```toml
    SUPABASE_URL = "your-project-url-here"
    SUPABASE_KEY = "your-anon-key-here"
    ```
    
    #### 5️⃣ Test Connection
    """)
    
    if st.button("🔄 Test Database Connection"):
        if SUPABASE_CONNECTED:
            try:
                # Test query
                result = supabase.table('products').select("count").execute()
                st.success("✅ Database connection successful!")
                st.info(f"Current products count: {len(result.data) if result.data else 0}")
            except Exception as e:
                st.error(f"❌ Connection test failed: {e}")
        else:
            st.error("❌ Not connected. Please check your credentials.")
    
    st.markdown("---")
    st.info("💡 **Tip:** After setup, restart the Streamlit app to apply changes.")

# ============================================
# PAGE 1: ADD NEW PRODUCT
# ============================================

elif page == "➕ Add New Product":
    st.markdown('<div class="section-header">📦 Product Type Selection</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2])
    with col1:
        product_type = st.selectbox(
            "Select Product Type",
            ["Cricket Bat (Deep Customization)", "Simple Product", "Variable Product"],
            key="product_type"
        )
    
    st.markdown("---")
    
    # ============================================
    # BASIC PRODUCT DETAILS (ALL TYPES)
    # ============================================
    st.markdown('<div class="section-header">📝 Basic Product Details</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        product_name = st.text_input("Product Name*", placeholder="e.g., Anglar Reserve Edition Bat")
        sku = st.text_input("SKU", placeholder="BAT-001")
        regular_price = st.number_input("Regular Price (₹)*", min_value=0.0, step=100.0)
        sale_price = st.number_input("Sale Price (₹)", min_value=0.0, step=100.0)
    
    with col2:
        stock_status = st.selectbox("Stock Status", ["In Stock", "Out of Stock", "On Backorder"])
        stock_quantity = st.number_input("Stock Quantity", min_value=0, value=0)
        weight = st.number_input("Weight (kg)", min_value=0.0, step=0.1)
        product_category = st.text_input("Category", placeholder="Cricket Equipment, Bats")
    
    # Description
    st.markdown("**Product Description**")
    short_description = st.text_area("Short Description", height=100, placeholder="Brief product overview...")
    full_description = st.text_area("Full Description", height=150, placeholder="Detailed product description...")
    
    # Images
    st.markdown('<div class="section-header">🖼️ Product Images</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        main_image = st.file_uploader("Main Product Image*", type=['png', 'jpg', 'jpeg', 'webp'])
        if main_image:
            st.image(main_image, caption="Main Image Preview", width=200)
    with col2:
        gallery_images = st.file_uploader("Gallery Images (Multiple)", type=['png', 'jpg', 'jpeg', 'webp'], accept_multiple_files=True)
        if gallery_images:
            st.write(f"✅ {len(gallery_images)} images selected")
    
    # ============================================
    # VARIABLE PRODUCT SECTION
    # ============================================
    variations_data = []
    if product_type == "Variable Product":
        st.markdown('<div class="section-header">🔄 Product Variations</div>', unsafe_allow_html=True)
        
        num_variations = st.number_input("Number of Variations", min_value=1, max_value=10, value=1)
        
        for i in range(num_variations):
            with st.expander(f"Variation {i+1}", expanded=True):
                col1, col2, col3 = st.columns(3)
                with col1:
                    var_name = st.text_input(f"Variation Name", key=f"var_name_{i}", placeholder="e.g., Size: Large")
                with col2:
                    var_price = st.number_input(f"Price (₹)", min_value=0.0, step=100.0, key=f"var_price_{i}")
                with col3:
                    var_sku = st.text_input(f"SKU", key=f"var_sku_{i}", placeholder="BAT-001-L")
                
                col4, col5 = st.columns(2)
                with col4:
                    var_stock = st.number_input(f"Stock", min_value=0, key=f"var_stock_{i}")
                with col5:
                    var_image = st.file_uploader(f"Variation Image", type=['png', 'jpg', 'jpeg'], key=f"var_image_{i}")
                
                variations_data.append({
                    'name': var_name,
                    'price': var_price,
                    'sku': var_sku,
                    'stock': var_stock,
                    'image': var_image
                })
    
    # ============================================
    # BAT DEEP CUSTOMIZATION
    # ============================================
    deep_custom_data = {}
    if product_type == "Cricket Bat (Deep Customization)":
        st.markdown('<div class="section-header">🏏 Deep Customization Options</div>', unsafe_allow_html=True)
        
        enable_deep_custom = st.checkbox("Enable Deep Customization", value=True)
        
        if enable_deep_custom:
            
            # Edition Information
            st.markdown("### 📘 Edition Information")
            col1, col2 = st.columns(2)
            with col1:
                edition_heading = st.text_input("Edition Heading", placeholder="Reserve Edition")
                edition_subtitle = st.text_input("Edition Short Subtitle", placeholder="Premium Willow Collection")
                edition_image = st.file_uploader("Edition Image", type=['png', 'jpg', 'jpeg'], key="edition_img")
            with col2:
                short_edition_desc = st.text_area("Short Edition Description", height=100)
                grains = st.text_input("Grains", placeholder="6-8 Grains")
                grade = st.text_input("Grade", placeholder="Grade A+")
                grain_description = st.text_area("Grain Description", height=100)
            
            # Handle options (simplified for brevity - you can expand these)
            st.markdown("### 🔧 Customization Options")
            
            # Handle Shape
            handle_shapes = []
            num_handle_shapes = st.number_input("Number of Handle Shapes", min_value=1, max_value=5, value=2)
            cols = st.columns(min(num_handle_shapes, 3))
            for i in range(num_handle_shapes):
                with cols[i % 3]:
                    shape = st.text_input(f"Shape {i+1}", key=f"shape_{i}", placeholder="Round")
                    if shape:
                        handle_shapes.append({'label': shape})
            
            # Laser Engraving
            st.markdown("### ✨ Laser Engraving")
            col1, col2 = st.columns(2)
            with col1:
                enable_laser = st.checkbox("Enable Laser Engraving", value=True)
                laser_price = st.number_input("Price (₹)", min_value=0.0, value=5.49) if enable_laser else 0
            with col2:
                laser_max_chars = st.number_input("Max Characters", min_value=1, value=8) if enable_laser else 0
                laser_image = st.file_uploader("Bat Image", type=['png', 'jpg'], key="laser_img") if enable_laser else None
            
            # Store deep customization data
            deep_custom_data = {
                'enabled': True,
                'edition': {
                    'heading': edition_heading,
                    'subtitle': edition_subtitle,
                    'short_description': short_edition_desc,
                    'grains': grains,
                    'grade': grade,
                    'grain_description': grain_description,
                    'image': edition_image
                },
                'handle_shapes': handle_shapes,
                'laser_engraving': {
                    'enabled': enable_laser,
                    'price': laser_price,
                    'max_chars': laser_max_chars,
                    'image': laser_image
                }
            }
    
    # ============================================
    # SAVE BUTTON WITH SUPABASE
    # ============================================
    st.markdown("---")
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        if st.button("💾 Save to Database", type="primary", use_container_width=True):
            if not product_name or regular_price == 0:
                st.error("❌ Please fill in Product Name and Regular Price")
            elif not SUPABASE_CONNECTED:
                st.error("❌ Database not connected. Check setup.")
            else:
                # Create progress indicators
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                try:
                    # Upload main image
                    status_text.text("⏳ Step 1/5: Uploading main image...")
                    progress_bar.progress(10)
                    main_image_data = upload_image_to_supabase(main_image, "products/main") if main_image else None
                    
                    # Upload gallery images
                    status_text.text("⏳ Step 2/5: Uploading gallery images...")
                    progress_bar.progress(25)
                    gallery_data = []
                    if gallery_images:
                        for idx, img in enumerate(gallery_images):
                            img_data = upload_image_to_supabase(img, "products/gallery")
                            if img_data:
                                gallery_data.append(img_data)
                            progress_bar.progress(25 + (idx + 1) * 15 // len(gallery_images))
                    else:
                        progress_bar.progress(40)
                    
                    # Upload variation images
                    status_text.text("⏳ Step 3/5: Processing variations...")
                    progress_bar.progress(50)
                    if product_type == "Variable Product":
                        for var in variations_data:
                            if var['image']:
                                var['image'] = upload_image_to_supabase(var['image'], "products/variations")
                    
                    # Upload deep customization images
                    status_text.text("⏳ Step 4/5: Uploading customization images...")
                    progress_bar.progress(65)
                    if product_type == "Cricket Bat (Deep Customization)" and enable_deep_custom:
                        if deep_custom_data['edition']['image']:
                            deep_custom_data['edition']['image'] = upload_image_to_supabase(
                                deep_custom_data['edition']['image'], 
                                "products/edition"
                            )
                        if deep_custom_data['laser_engraving']['image']:
                            deep_custom_data['laser_engraving']['image'] = upload_image_to_supabase(
                                deep_custom_data['laser_engraving']['image'], 
                                "products/laser"
                            )
                    
                    # Compile product data
                    progress_bar.progress(80)
                    product_data = {
                        'product_name': product_name,
                        'product_type': product_type,
                        'sku': sku,
                        'regular_price': float(regular_price),
                        'sale_price': float(sale_price) if sale_price else None,
                        'stock_status': stock_status,
                        'stock_quantity': int(stock_quantity),
                        'weight': float(weight) if weight else None,
                        'category': product_category,
                        'short_description': short_description,
                        'full_description': full_description,
                        'main_image': main_image_data,
                        'gallery_images': gallery_data,
                        'variations': variations_data if product_type == "Variable Product" else None,
                        'deep_customization': deep_custom_data if product_type == "Cricket Bat (Deep Customization)" else None,
                        'product_data': {
                            'timestamp': datetime.now().isoformat(),
                            'complete_data': 'Full product structure here'
                        }
                    }
                    
                    # Save to Supabase
                    status_text.text("⏳ Step 5/5: Saving to database...")
                    progress_bar.progress(90)
                    result = save_product_to_supabase(product_data)
                    
                    progress_bar.progress(100)
                    status_text.text("✅ Complete!")
                    
                    if result:
                        st.success(f"✅ Product '{product_name}' saved successfully to database!")
                        st.balloons()
                        
                        # Show product ID
                        # Show product details
                        with st.expander("📝 View Saved Product Details", expanded=True):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write(f"**Product ID:** {result['id']}")
                                st.write(f"**Name:** {product_name}")
                                st.write(f"**Type:** {product_type}")
                                st.write(f"**Price:** ₹{regular_price:,.2f}")
                            with col2:
                                st.write(f"**SKU:** {sku or 'N/A'}")
                                st.write(f"**Stock:** {stock_status}")
                                st.write(f"**Quantity:** {stock_quantity}")
                                if main_image_data:
                                    st.image(main_image_data['url'], width=150, caption="Main Image")
                        
                        # Add another product button
                        col_a, col_b, col_c = st.columns([2, 1, 2])
                        with col_b:
                            if st.button("➕ Add Another Product", key="add_another", use_container_width=True):
                                st.rerun()
                    else:
                        st.error("❌ Failed to save product. Check error messages above.")
                
                except Exception as e:
                    logger.error(f"Error in save process: {e}")
                    st.error(f"❌ Error during save: {e}")
                
                finally:
                    # Clean up progress indicators after 2 seconds
                    import time
                    time.sleep(2)
                    progress_bar.empty()
                    status_text.empty()

# ============================================
# PAGE 2: VIEW ALL PRODUCTS
# ============================================

elif page == "📋 View All Products":
    st.markdown('<div class="section-header">📋 All Products</div>', unsafe_allow_html=True)
    
    if not SUPABASE_CONNECTED:
        st.warning("⚠️ Database not connected. Cannot fetch products.")
    else:
        products = get_all_products_from_supabase()
        
        if len(products) == 0:
            st.info("📦 No products in database yet. Start by adding a new product!")
        else:
            # Summary cards
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{len(products)}</div>
                    <div class="metric-label">Total Products</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                bat_count = sum(1 for p in products if p.get('product_type') == "Cricket Bat (Deep Customization)")
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{bat_count}</div>
                    <div class="metric-label">Cricket Bats</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                in_stock = sum(1 for p in products if p.get('stock_status') == "In Stock")
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{in_stock}</div>
                    <div class="metric-label">In Stock</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col4:
                total_value = sum(float(p.get('regular_price', 0)) for p in products)
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">₹{total_value:,.0f}</div>
                    <div class="metric-label">Total Value</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Display products in cards
            for product in products:
                with st.container():
                    st.markdown('<div class="product-card">', unsafe_allow_html=True)
                    
                    col1, col2, col3 = st.columns([2, 2, 1])
                    
                    with col1:
                        st.markdown(f"### 🏏 {product.get('product_name', 'Unnamed Product')}")
                        st.markdown(f"**SKU:** {product.get('sku', 'N/A')}")
                        st.markdown(f"**Type:** {product.get('product_type', 'N/A')}")
                    
                    with col2:
                        st.markdown(f"**Price:** ₹{product.get('regular_price', 0):,.2f}")
                        st.markdown(f"**Stock:** {product.get('stock_status', 'N/A')} ({product.get('stock_quantity', 0)} units)")
                        st.markdown(f"**Category:** {product.get('category', 'N/A')}")
                    
                    with col3:
                        # Show main image if available
                        if product.get('main_image') and product['main_image'].get('url'):
                            st.image(product['main_image']['url'], width=100)
                    
                    # Action buttons
                    col1, col2, col3 = st.columns([1, 1, 3])
                    with col1:
                        if st.button("👁️ View Details", key=f"view_{product['id']}"):
                            st.json(product)
                    with col2:
                        if st.button("🗑️ Delete", key=f"delete_{product['id']}", type="secondary"):
                            # Add confirmation
                            if st.session_state.get(f"confirm_delete_{product['id']}", False):
                                if delete_product_from_supabase(product['id']):
                                    st.success("✅ Product deleted!")
                                    logger.info(f"Product deleted: {product.get('product_name')}")
                                    st.rerun()
                                else:
                                    st.error("❌ Failed to delete product")
                            else:
                                st.session_state[f"confirm_delete_{product['id']}"] = True
                                st.warning("⚠️ Click delete again to confirm")
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                    st.markdown("---")

# ============================================
# PAGE 3: SEARCH PRODUCTS
# ============================================

elif page == "🔍 Search Products":
    st.markdown('<div class="section-header">🔍 Search Products</div>', unsafe_allow_html=True)
    
    if not SUPABASE_CONNECTED:
        st.warning("⚠️ Database not connected.")
    else:
        search_query = st.text_input("🔎 Search by product name or SKU", placeholder="Type to search...")
        
        if search_query:
            results = search_products(search_query)
            
            if results:
                st.success(f"Found {len(results)} product(s)")
                
                for product in results:
                    with st.expander(f"🏏 {product.get('product_name')} - {product.get('sku')}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown(f"**Price:** ₹{product.get('regular_price', 0):,.2f}")
                            st.markdown(f"**Type:** {product.get('product_type')}")
                        with col2:
                            st.markdown(f"**Stock:** {product.get('stock_status')}")
                            st.markdown(f"**Category:** {product.get('category')}")
                        
                        if st.button("View Full Details", key=f"search_view_{product['id']}"):
                            st.json(product)
            else:
                st.info("No products found matching your search.")

# ============================================
# PAGE 4: EXPORT DATA
# ============================================

elif page == "📊 Export Data":
    st.markdown('<div class="section-header">📊 Export Product Data</div>', unsafe_allow_html=True)
    
    if not SUPABASE_CONNECTED:
        st.warning("⚠️ Database not connected.")
    else:
        products = get_all_products_from_supabase()
        
        if len(products) == 0:
            st.warning("No products to export.")
        else:
            st.info(f"Ready to export {len(products)} products")
            
            # Export as JSON
            st.markdown("### 📄 Export as JSON")
            json_data = json.dumps(products, indent=2, default=str)
            st.download_button(
                label="⬇️ Download JSON",
                data=json_data,
                file_name=f"products_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                use_container_width=True
            )
            
            st.markdown("---")
            
            # Export as Excel
            st.markdown("### 📊 Export as Excel (Basic Info)")
            
            # Create basic info dataframe
            basic_data = []
            for product in products:
                basic_data.append({
                    'Product ID': product.get('id', ''),
                    'Product Name': product.get('product_name', ''),
                    'Type': product.get('product_type', ''),
                    'SKU': product.get('sku', ''),
                    'Regular Price': product.get('regular_price', 0),
                    'Sale Price': product.get('sale_price', 0),
                    'Stock Status': product.get('stock_status', ''),
                    'Stock Quantity': product.get('stock_quantity', 0),
                    'Category': product.get('category', ''),
                    'Weight': product.get('weight', 0),
                    'Created At': product.get('created_at', '')[:10] if product.get('created_at') else ''
                })
            
            df = pd.DataFrame(basic_data)
            
            # Convert to Excel
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Products')
                
                # Add a sheet for deep customization if any bat products exist
                bat_products = [p for p in products if p.get('product_type') == 'Cricket Bat (Deep Customization)']
                if bat_products:
                    bat_data = []
                    for product in bat_products:
                        deep_custom = product.get('deep_customization', {})
                        if deep_custom:
                            edition = deep_custom.get('edition', {})
                            laser = deep_custom.get('laser_engraving', {})
                            bat_data.append({
                                'Product Name': product.get('product_name', ''),
                                'SKU': product.get('sku', ''),
                                'Edition Heading': edition.get('heading', ''),
                                'Grains': edition.get('grains', ''),
                                'Grade': edition.get('grade', ''),
                                'Laser Engraving': 'Yes' if laser.get('enabled') else 'No',
                                'Laser Price': laser.get('price', 0)
                            })
                    
                    if bat_data:
                        df_bats = pd.DataFrame(bat_data)
                        df_bats.to_excel(writer, index=False, sheet_name='Bat Customization')
            
            excel_data = output.getvalue()
            
            st.download_button(
                label="⬇️ Download Excel",
                data=excel_data,
                file_name=f"products_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
            
            st.markdown("---")
            
            # Export as CSV
            st.markdown("### 📋 Export as CSV")
            csv_data = df.to_csv(index=False)
            st.download_button(
                label="⬇️ Download CSV",
                data=csv_data,
                file_name=f"products_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
            
            st.markdown("---")
            st.markdown("### 👁️ Preview Data")
            st.dataframe(df, use_container_width=True)
            
            # Product count by type
            st.markdown("---")            
            
            st.markdown("### 📊 Analytics")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Products by Type**")
                type_counts = {}
                for product in products:
                    ptype = product.get('product_type', 'Unknown')
                    type_counts[ptype] = type_counts.get(ptype, 0) + 1
                
                for ptype, count in type_counts.items():
                    st.write(f"- {ptype}: {count}")
            
            with col2:
                st.markdown("**Stock Status**")
                stock_counts = {}
                for product in products:
                    status = product.get('stock_status', 'Unknown')
                    stock_counts[status] = stock_counts.get(status, 0) + 1
                
                for status, count in stock_counts.items():
                    st.write(f"- {status}: {count}")
            # Database Backup
            st.markdown("### 💾 Full Database Backup")
            st.info("📦 Create a complete backup of all products including metadata and statistics")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🔄 Create Full Backup", use_container_width=True):
                    backup_data = {
                        'backup_info': {
                            'created_at': datetime.now().isoformat(),
                            'total_products': len(products),
                            'app_version': 'v2.0',
                            'database': 'Supabase'
                        },
                        'products': products,
                        'statistics': {
                            'by_type': type_counts,
                            'by_stock': stock_counts,
                            'total_value': float(total_value)
                        }
                    }
                    
                    backup_json = json.dumps(backup_data, indent=2, default=str)
                    
                    st.download_button(
                        label="⬇️ Download Full Backup (JSON)",
                        data=backup_json,
                        file_name=f"full_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json",
                        use_container_width=True,
                        key="download_backup"
                    )
                    
                    st.success("✅ Backup file ready for download!")
                    logger.info(f"Backup created with {len(products)} products")
            
            with col2:
                st.markdown("**Backup includes:**")
                st.write("- All product data")
                st.write("- Product images URLs")
                st.write("- Statistics & analytics")
                st.write("- Timestamp & metadata")
# ============================================
# FOOTER
# ============================================
st.markdown("---")
    
    

st.markdown(
    """
    <div style='text-align: center; color: #666; padding: 2rem 0;'>
        <p>🏏 Product Data Collection System </p>
    </div>
    """,
    unsafe_allow_html=True
)