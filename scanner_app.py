import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import json
import os

# ── Page config — called ONCE at the very top, never again ───────────────────
st.set_page_config(
    page_title="AI Document Scanner",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── Custom CSS — nicer look ───────────────────────────────────────────────────
st.markdown("""
<style>
    /* Main background */
    .stApp { background-color: #F3F4F6; }

    /* Hide default Streamlit header */
    header[data-testid="stHeader"] { background: transparent; }

    /* App title area */
    .app-header {
        background: linear-gradient(135deg, #1E1B4B 0%, #3C3489 100%);
        color: white;
        padding: 2rem 2.5rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
    }
    .app-header h1 { color: white; font-size: 2rem; margin: 0 0 0.3rem 0; }
    .app-header p  { color: #AFA9EC; margin: 0; font-size: 1rem; }

    /* Cards */
    .scan-card {
        background: white;
        border-radius: 14px;
        padding: 1.5rem;
        border: 1px solid #E5E7EB;
        height: 100%;
    }
    .scan-card h3 { color: #1E1B4B; font-size: 1.1rem; margin-bottom: 1rem; }

    /* Result item boxes */
    .result-item {
        background: #F8F8FC;
        border-left: 4px solid #7F77DD;
        border-radius: 0 8px 8px 0;
        padding: 0.6rem 1rem;
        margin-bottom: 0.5rem;
        font-size: 0.9rem;
    }
    .result-label { color: #64748B; font-size: 0.75rem; font-weight: 600;
                    text-transform: uppercase; letter-spacing: 0.05em; }
    .result-value { color: #1E1B4B; font-size: 0.95rem; margin-top: 2px; }

    /* Status badges */
    .badge {
        display: inline-block;
        padding: 3px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-bottom: 1rem;
    }
    .badge-receipt  { background: #EAF3DE; color: #3B6D11; }
    .badge-card     { background: #E6F1FB; color: #185FA5; }
    .badge-note     { background: #EEEDFE; color: #3C3489; }
    .badge-other    { background: #FAEEDA; color: #854F0B; }

    /* Total highlight */
    .total-box {
        background: #1E1B4B;
        color: white;
        border-radius: 10px;
        padding: 1rem 1.5rem;
        margin-top: 1rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .total-label { font-size: 0.85rem; opacity: 0.7; }
    .total-amount { font-size: 1.5rem; font-weight: 700; }

    /* Upload area */
    [data-testid="stFileUploader"] > div {
        border: 2px dashed #A5B4FC !important;
        border-radius: 12px !important;
        background: #FAFAFA !important;
    }

    /* Scan button */
    .stButton > button {
        background: #7F77DD !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        padding: 0.65rem 1.5rem !important;
        width: 100% !important;
        transition: background 0.2s !important;
    }
    .stButton > button:hover { background: #6B63CC !important; }

    /* Error / info boxes */
    .tip-box {
        background: #E6F1FB;
        border-radius: 10px;
        padding: 0.8rem 1rem;
        color: #185FA5;
        font-size: 0.88rem;
        margin-top: 0.5rem;
    }
    .warn-box {
        background: #FAEEDA;
        border-radius: 10px;
        padding: 0.8rem 1rem;
        color: #854F0B;
        font-size: 0.88rem;
        margin-top: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="app-header">
    <h1>🧾 AI Document Scanner</h1>
    <p>Upload a receipt, invoice, business card or handwritten note — AI extracts everything instantly</p>
</div>
""", unsafe_allow_html=True)


# ── API Key setup — safe, from environment or sidebar input ──────────────────
# First try environment variable (best practice)
# Try Streamlit secrets first (when deployed on Streamlit Cloud)
# Fall back to environment variable (when running locally)
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except (KeyError, FileNotFoundError):
    api_key = os.environ.get("GEMINI_API_KEY", "")

# If not set, let the user enter it in the sidebar
if not api_key:
    with st.sidebar:
        st.markdown("### 🔑 API Key")
        api_key = st.text_input(
            "Enter your Gemini API key",
            type="password",
            placeholder="AIzaSy...",
            help="Get a free key at aistudio.google.com — no credit card needed"
        )
        st.markdown("""
        <div class="tip-box">
            Get your free key at<br>
            <b>aistudio.google.com</b><br>
            No credit card required.
        </div>
        """, unsafe_allow_html=True)

if not api_key:
    st.info("👈  Enter your Gemini API key in the sidebar to get started. It's free — no credit card needed.")
    st.markdown("""
    <div class="tip-box">
        🔗 Go to <b>aistudio.google.com</b> → sign in with Google → click <b>Get API key</b> → paste it in the sidebar.
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# Initialise the Gemini client
try:
    client = genai.Client(api_key=api_key)
except Exception as e:
    st.error(f"Could not connect to Gemini API: {e}")
    st.stop()


# ── Two-column layout ─────────────────────────────────────────────────────────
left_col, right_col = st.columns([1, 1], gap="large")


# ── LEFT: Upload + Preview ────────────────────────────────────────────────────
with left_col:
    st.markdown('<div class="scan-card">', unsafe_allow_html=True)
    st.markdown("### 📷 Upload your document")

    uploaded_file = st.file_uploader(
        "Drag and drop or click to browse",
        type=["jpg", "jpeg", "png", "webp"],
        label_visibility="collapsed"
    )

    if uploaded_file:
        # Open image with PIL
        image = Image.open(uploaded_file)
        st.image(image, caption="Your uploaded document", use_container_width=True)

        # Show file info
        st.markdown(f"""
        <div class="tip-box">
            📄 <b>{uploaded_file.name}</b><br>
            Size: {uploaded_file.size // 1024} KB &nbsp;|&nbsp;
            Type: {uploaded_file.type}
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Scan button
        scan_clicked = st.button("🔍  Scan with AI", type="primary")
    else:
        st.markdown("""
        <div style="text-align:center; padding: 3rem 1rem; color: #94A3B8;">
            <div style="font-size: 3rem;">📄</div>
            <div style="font-size: 0.95rem; margin-top: 0.5rem;">
                Upload a receipt, invoice,<br>business card or handwritten note
            </div>
        </div>
        """, unsafe_allow_html=True)
        scan_clicked = False

    st.markdown('</div>', unsafe_allow_html=True)


# ── RIGHT: Results ────────────────────────────────────────────────────────────
with right_col:
    st.markdown('<div class="scan-card">', unsafe_allow_html=True)
    st.markdown("### 📊 Extracted information")

    if not uploaded_file:
        st.markdown("""
        <div style="text-align:center; padding: 3rem 1rem; color: #94A3B8;">
            <div style="font-size: 3rem;">✨</div>
            <div style="font-size: 0.95rem; margin-top: 0.5rem;">
                Results will appear here<br>after you upload and scan
            </div>
        </div>
        """, unsafe_allow_html=True)

    elif scan_clicked:
        with st.spinner("AI is reading your document..."):

            # ── Convert image to bytes correctly ──────────────────────────
            # Save to buffer using a safe format (never use image.format raw)
            buf = io.BytesIO()
            fmt = image.format if image.format in ("JPEG", "PNG", "WEBP") else "JPEG"
            save_image = image.convert("RGB") if fmt == "JPEG" else image
            save_image.save(buf, format=fmt)
            image_bytes = buf.getvalue()
            mime = f"image/{fmt.lower()}"

            # ── Build the prompt ──────────────────────────────────────────
            prompt = """
You are an expert document scanner. Carefully look at this image.

Extract ALL useful information and return it as VALID JSON ONLY.
No extra text, no markdown code fences, just the raw JSON object.

RULES:
- If it is a RECEIPT or INVOICE, return:
  {"type":"receipt","vendor":"...","date":"...","items":[{"name":"...","qty":"...","price":"..."}],"subtotal":"...","tax":"...","total":"...","currency":"...","confidence":"high/medium/low"}

- If it is a BUSINESS CARD, return:
  {"type":"business_card","name":"...","title":"...","company":"...","email":"...","phone":"...","website":"...","address":"...","confidence":"high/medium/low"}

- If it is a HANDWRITTEN NOTE, return:
  {"type":"note","content":"...","key_points":["...","..."],"confidence":"high/medium/low"}

- If it is something else (menu, form, ID, etc.), return:
  {"type":"other","document_description":"...","extracted_text":"...","key_fields":{"field":"value"},"confidence":"high/medium/low"}

Use "N/A" for fields you cannot read. Always include the confidence field.
"""

            try:
                # ── Call Gemini — correct 2026 SDK syntax ─────────────────
                # Pass PIL image directly — the SDK handles base64 conversion
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[
                        image,   # PIL Image passed directly — correct syntax
                        prompt
                    ]
                )

                raw = response.text.strip()

                # Clean up in case model wraps in ```json ... ```
                if raw.startswith("```"):
                    raw = raw.split("```")[1]
                    if raw.startswith("json"):
                        raw = raw[4:]
                raw = raw.strip()

                data = json.loads(raw)

                # ── Display results based on document type ─────────────────
                doc_type = data.get("type", "other")
                confidence = data.get("confidence", "unknown")
                conf_color = {"high": "#3B6D11", "medium": "#854F0B", "low": "#A32D2D"}.get(confidence, "#64748B")
                conf_bg    = {"high": "#EAF3DE", "medium": "#FAEEDA", "low": "#FCEBEB"}.get(confidence, "#F1EFE8")

                # Badge row
                badge_class = {"receipt": "badge-receipt", "business_card": "badge-card",
                               "note": "badge-note"}.get(doc_type, "badge-other")
                badge_label = {"receipt": "🧾 Receipt / Invoice", "business_card": "👤 Business Card",
                               "note": "✏️ Handwritten Note"}.get(doc_type, "📄 Document")

                st.markdown(f"""
                <span class="badge {badge_class}">{badge_label}</span>
                <span class="badge" style="background:{conf_bg};color:{conf_color}">
                    Confidence: {confidence.upper()}
                </span>
                """, unsafe_allow_html=True)

                # ── RECEIPT ────────────────────────────────────────────────
                if doc_type in ("receipt", "invoice"):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.markdown(f"""
                        <div class="result-item">
                            <div class="result-label">Vendor / Store</div>
                            <div class="result-value">{data.get("vendor", "N/A")}</div>
                        </div>""", unsafe_allow_html=True)
                    with col_b:
                        st.markdown(f"""
                        <div class="result-item">
                            <div class="result-label">Date</div>
                            <div class="result-value">{data.get("date", "N/A")}</div>
                        </div>""", unsafe_allow_html=True)

                    items = data.get("items", [])
                    if items:
                        st.markdown("**Items purchased:**")
                        # Build a clean table
                        table_rows = "".join([
                            f"<tr><td style='padding:8px 10px'>{i.get('name','')}</td>"
                            f"<td style='padding:8px 10px;text-align:center'>{i.get('qty','')}</td>"
                            f"<td style='padding:8px 10px;text-align:right'>{i.get('price','')}</td></tr>"
                            for i in items
                        ])
                        st.markdown(f"""
                        <table style='width:100%;border-collapse:collapse;font-size:0.9rem;
                                       border:1px solid #E5E7EB;border-radius:8px;overflow:hidden'>
                            <thead>
                                <tr style='background:#1E1B4B;color:white'>
                                    <th style='padding:10px;text-align:left'>Item</th>
                                    <th style='padding:10px;text-align:center'>Qty</th>
                                    <th style='padding:10px;text-align:right'>Price</th>
                                </tr>
                            </thead>
                            <tbody>{table_rows}</tbody>
                        </table>
                        """, unsafe_allow_html=True)

                    # Totals
                    currency = data.get("currency", "")
                    if data.get("subtotal") and data.get("subtotal") != "N/A":
                        st.markdown(f"""
                        <div class="result-item" style="margin-top:0.8rem">
                            <div class="result-label">Subtotal</div>
                            <div class="result-value">{currency} {data.get("subtotal","")}</div>
                        </div>""", unsafe_allow_html=True)
                    if data.get("tax") and data.get("tax") != "N/A":
                        st.markdown(f"""
                        <div class="result-item">
                            <div class="result-label">Tax</div>
                            <div class="result-value">{currency} {data.get("tax","")}</div>
                        </div>""", unsafe_allow_html=True)
                    if data.get("total") and data.get("total") != "N/A":
                        st.markdown(f"""
                        <div class="total-box">
                            <span class="total-label">TOTAL AMOUNT</span>
                            <span class="total-amount">{currency} {data.get("total","")}</span>
                        </div>""", unsafe_allow_html=True)

                # ── BUSINESS CARD ──────────────────────────────────────────
                elif doc_type == "business_card":
                    fields = [
                        ("👤 Name",    data.get("name")),
                        ("💼 Title",   data.get("title")),
                        ("🏢 Company", data.get("company")),
                        ("✉️ Email",   data.get("email")),
                        ("📞 Phone",   data.get("phone")),
                        ("🌐 Website", data.get("website")),
                        ("📍 Address", data.get("address")),
                    ]
                    for label, value in fields:
                        if value and value != "N/A":
                            st.markdown(f"""
                            <div class="result-item">
                                <div class="result-label">{label}</div>
                                <div class="result-value">{value}</div>
                            </div>""", unsafe_allow_html=True)

                # ── HANDWRITTEN NOTE ───────────────────────────────────────
                elif doc_type == "note":
                    st.markdown("**Full text:**")
                    st.markdown(f"""
                    <div style='background:#F8F8FC;border-radius:10px;padding:1rem;
                                font-size:0.95rem;color:#1E1B4B;line-height:1.7'>
                        {data.get("content", "Could not read")}
                    </div>""", unsafe_allow_html=True)
                    points = data.get("key_points", [])
                    if points:
                        st.markdown("**Key points:**")
                        for p in points:
                            st.markdown(f"• {p}")

                # ── OTHER / GENERIC ────────────────────────────────────────
                else:
                    st.markdown(f"""
                    <div class="result-item">
                        <div class="result-label">Document type</div>
                        <div class="result-value">{data.get("document_description","Unknown")}</div>
                    </div>""", unsafe_allow_html=True)

                    extracted = data.get("extracted_text", "")
                    if extracted:
                        st.markdown("**Extracted text:**")
                        st.markdown(f"""
                        <div style='background:#F8F8FC;border-radius:10px;padding:1rem;
                                    font-size:0.9rem;color:#1E1B4B;line-height:1.7'>
                            {extracted}
                        </div>""", unsafe_allow_html=True)

                    key_fields = data.get("key_fields", {})
                    for k, v in key_fields.items():
                        st.markdown(f"""
                        <div class="result-item">
                            <div class="result-label">{k}</div>
                            <div class="result-value">{v}</div>
                        </div>""", unsafe_allow_html=True)

                # ── Raw JSON expander (useful for learning) ────────────────
                with st.expander("🔍 View raw AI response (JSON)"):
                    st.json(data)

                st.success("✅ Scan complete!")

            except json.JSONDecodeError:
                # AI responded but not in JSON — show it as plain text anyway
                st.warning("AI responded but not in expected format. Showing raw response:")
                st.markdown(raw)

            except Exception as e:
                err = str(e)
                if "API_KEY" in err.upper() or "401" in err:
                    st.error("❌ Invalid API key. Check your key at aistudio.google.com")
                elif "quota" in err.lower() or "429" in err:
                    st.error("❌ You have hit the rate limit. Wait a minute and try again.")
                elif "SAFETY" in err.upper():
                    st.error("❌ Image was blocked by safety filters. Try a different image.")
                else:
                    st.error(f"❌ Something went wrong: {e}")

    else:
        # Uploaded but not yet scanned
        st.markdown("""
        <div style="text-align:center; padding: 3rem 1rem; color: #94A3B8;">
            <div style="font-size: 3rem;">👈</div>
            <div style="font-size: 0.95rem; margin-top: 0.5rem;">
                Click <b>Scan with AI</b><br>to extract the data
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


# ── Footer tips ───────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("""
    <div class="tip-box">
        📸 <b>Best results tip</b><br>
        Use clear, well-lit photos. Avoid blurry or dark images.
    </div>""", unsafe_allow_html=True)
with c2:
    st.markdown("""
    <div class="tip-box">
        🌍 <b>Works in any language</b><br>
        Gemini can read receipts in English, French, Arabic, and more.
    </div>""", unsafe_allow_html=True)
with c3:
    st.markdown("""
    <div class="tip-box">
        🔑 <b>Free API key</b><br>
        Get yours at aistudio.google.com — 500 free scans per day.
    </div>""", unsafe_allow_html=True)
