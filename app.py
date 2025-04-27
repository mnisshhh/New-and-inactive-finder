import streamlit as st
import pandas as pd
from io import BytesIO
import zipfile
import time

# Streamlit page config
st.set_page_config(page_title="Data Comparator", layout="centered")
st.title("📚 Data Cleaner & Comparator")

# Project Selector
project_type = st.selectbox("Select Project Type", ["Gardners", "Bookazine"])

# Helper Functions
def clean_gardners(df, removal_list):
    drop_cols = [4, 7, 8, 9, 14, 15, 16, 17, 18, 19]
    df = df.drop(df.columns[drop_cols], axis=1)

    df['WEIGHT'] = pd.to_numeric(df['WEIGHT'], errors='coerce')
    df = df.dropna(subset=['WEIGHT'])
    df = df[~df['WEIGHT'].isin([0, 1])]
    df = df.reset_index(drop=True)

    rest_cols = df.columns[3:9]
    df[rest_cols] = df[rest_cols].apply(pd.to_numeric, errors='coerce')
    df = df.dropna(subset=['DIM1'])
    df = df[~df['DIM1'].isin([0])]
    df = df.reset_index(drop=True)

    df = df[~df['STOCK'].isin([0])]
    df = df.reset_index(drop=True)

    df['ISBN13'] = pd.to_numeric(df['ISBN13'], errors='coerce')
    df = df.dropna(subset=['ISBN13'])

    df = df[~df['ISBN13'].isin(removal_list)]
    df = df.reset_index(drop=True)

    return df

def clean_bookazine(df, removal_list):
    drop_cols = ['D', 'F', 'I', 'J', 'O']
    df = df.drop(columns=drop_cols, errors='ignore')

    df['WGT OZS'] = pd.to_numeric(df['WGT OZS'], errors='coerce')
    df = df.dropna(subset=['WGT OZS'])
    df = df[~df['WGT OZS'].isin([0])]
    df = df.reset_index(drop=True)

    df['QTYAV'] = pd.to_numeric(df['QTYAV'], errors='coerce')
    df = df.dropna(subset=['QTYAV'])
    df = df[~df['QTYAV'].isin([0])]
    df = df.reset_index(drop=True)

    df['EAN #'] = pd.to_numeric(df['EAN #'], errors='coerce')
    df = df.dropna(subset=['EAN #'])

    df = df[~df['EAN #'].isin(removal_list)]
    df = df.reset_index(drop=True)

    return df

def to_csv(df):
    output = BytesIO()
    df.to_csv(output, index=False)
    return output.getvalue()

# Upload Files
uploaded_old = st.file_uploader("Upload OLD File (.xlsx)", type=["xlsx"])
uploaded_new = st.file_uploader("Upload NEW File (.xlsx)", type=["xlsx"])
uploaded_removal = st.file_uploader("Upload REMOVAL List (.xlsx)", type=["xlsx"])

# Key Columns
if project_type == "Gardners":
    key_column = 'ISBN13'
    removal_column = 'ISBN13'
elif project_type == "Bookazine":
    key_column = 'EAN #'
    removal_column = 'EAN #'

# Process
if st.button("🚀 Process Files"):
    if uploaded_old and uploaded_new and uploaded_removal:
        with st.spinner('Processing files...'):

            progress = st.progress(0)
            status_text = st.empty()

            # Step 1: Read Files
            status_text.text("Reading uploaded files...")
            old_df = pd.read_excel(uploaded_old, skiprows=2) if project_type == "Gardners" else pd.read_excel(uploaded_old)
            new_df = pd.read_excel(uploaded_new, skiprows=2) if project_type == "Gardners" else pd.read_excel(uploaded_new)
            removal_list = pd.read_excel(uploaded_removal)[removal_column].astype(float).tolist()
            progress.progress(25)

            # Step 2: Clean Files
            status_text.text("Cleaning OLD file...")
            cleaned_old = clean_gardners(old_df, removal_list) if project_type == "Gardners" else clean_bookazine(old_df, removal_list)
            progress.progress(50)

            status_text.text("Cleaning NEW file...")
            cleaned_new = clean_gardners(new_df, removal_list) if project_type == "Gardners" else clean_bookazine(new_df, removal_list)
            progress.progress(70)

            # Step 3: Find New & Inactive Items
            status_text.text("Finding New & Inactive Items...")
            new_items = cleaned_new[~cleaned_new[key_column].isin(cleaned_old[key_column])]
            inactive_items = cleaned_old[~cleaned_old[key_column].isin(cleaned_new[key_column])]
            progress.progress(90)

            # Pause before complete
            time.sleep(0.5)
            progress.progress(100)

        st.success(f"✅ Processing Complete!")
        st.write(f"🆕 New Items Found: {len(new_items)}")
        st.write(f"📦 Inactive Items Found: {len(inactive_items)}")

        # Previews
        st.subheader("🔍 Preview of New Items")
        st.dataframe(new_items.head())

        st.subheader("🔍 Preview of Inactive Items")
        st.dataframe(inactive_items.head())

        # Store in session_state for multi-downloads
        st.session_state['new_items'] = new_items
        st.session_state['inactive_items'] = inactive_items
        st.session_state['cleaned_new'] = cleaned_new
        st.session_state['processed'] = True

# Show download buttons if processed
if 'processed' in st.session_state and st.session_state['processed']:
    st.subheader("⬇️ Download Files")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.download_button("📥 New Items (CSV)", to_csv(st.session_state['new_items']), file_name="new_items.csv", mime="text/csv")
    with col2:
        st.download_button("📥 Inactive Items (CSV)", to_csv(st.session_state['inactive_items']), file_name="inactive_items.csv", mime="text/csv")
    with col3:
        st.download_button("📥 Cleaned NEW (CSV)", to_csv(st.session_state['cleaned_new']), file_name="cleaned_new.csv", mime="text/csv")

    # Zip download
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        zip_file.writestr("new_items.csv", to_csv(st.session_state['new_items']))
        zip_file.writestr("inactive_items.csv", to_csv(st.session_state['inactive_items']))
        zip_file.writestr("cleaned_new.csv", to_csv(st.session_state['cleaned_new']))
    zip_buffer.seek(0)

    st.download_button("📦 Download All as ZIP", zip_buffer, file_name="all_files.zip", mime="application/zip")
