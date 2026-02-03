import streamlit as st
import requests
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
# Correct import for TableOfContents
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.units import inch, cm
from io import BytesIO
import tempfile
import os

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="PDF Report Generator", layout="wide")

# --- SESSION STATE MANAGEMENT ---
if 'content_list' not in st.session_state:
    st.session_state.content_list = []

# --- HELPER FUNCTIONS FOR PDF GENERATION ---

class PDFGenerator:
    def __init__(self, buffer):
        self.buffer = buffer
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()

    def setup_custom_styles(self):
        # Using Times-Roman family to match the screenshot
        
        # Title Style (Bold, Large)
        self.styles.add(ParagraphStyle(
            name='CoverTitle',
            parent=self.styles['Title'],
            fontSize=18,
            leading=22,
            alignment=TA_CENTER,
            spaceAfter=12,
            fontName='Times-Bold'
        ))
        
        # Subtitle Style
        self.styles.add(ParagraphStyle(
            name='CoverSubtitle',
            parent=self.styles['Normal'],
            fontSize=14,
            leading=18,
            alignment=TA_CENTER,
            spaceAfter=40,
            fontName='Times-Roman'
        ))
        
        # "Submitted by" Bold Style
        self.styles.add(ParagraphStyle(
            name='SubmittedByLabel',
            parent=self.styles['Normal'],
            fontSize=12,
            leading=16,
            alignment=TA_CENTER,
            fontName='Times-Bold',
            spaceAfter=6
        ))

        # Student Details Style
        self.styles.add(ParagraphStyle(
            name='StudentInfo',
            parent=self.styles['Normal'],
            fontSize=12,
            leading=18,
            alignment=TA_CENTER,
            fontName='Times-Roman'
        ))

        # Institute Details at Bottom
        self.styles.add(ParagraphStyle(
            name='InstituteInfo',
            parent=self.styles['Normal'],
            fontSize=12,
            leading=16,
            alignment=TA_CENTER,
            fontName='Times-Roman'
        ))

        # Heading 1 for TOC (Content pages)
        self.styles.add(ParagraphStyle(
            name='CustomH1',
            parent=self.styles['Heading1'],
            fontSize=16,
            leading=20,
            spaceBefore=20,
            spaceAfter=10,
            fontName='Times-Bold'
        ))

        # Normal Body Text — override the built-in 'BodyText' style in place
        self.styles['BodyText'].fontSize = 11
        self.styles['BodyText'].leading = 14
        self.styles['BodyText'].alignment = TA_JUSTIFY
        self.styles['BodyText'].fontName = 'Times-Roman'

    def draw_cover_footer(self, canvas, doc):
        """
        Draws page number '0' on the cover page.
        """
        canvas.saveState()
        canvas.setFont('Times-Roman', 11)
        # Draw "0" at the bottom center
        canvas.drawCentredString(A4[0] / 2.0, 0.75 * inch, "0")
        canvas.restoreState()

    def draw_content_footer(self, canvas, doc):
        """
        Draws standard page numbers (1, 2, 3...) on subsequent pages.
        """
        page_num = canvas.getPageNumber()
        canvas.saveState()
        canvas.setFont('Times-Roman', 10)
        canvas.drawCentredString(A4[0] / 2.0, 0.5 * inch, str(page_num))
        canvas.restoreState()

    def fetch_logo(self, url):
        try:
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            if response.status_code == 200:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                    tmp.write(response.content)
                    return tmp.name
        except Exception as e:
            print(f"Error fetching logo: {e}")
        return None

    def generate(self, metadata, content_items):
        doc = SimpleDocTemplate(
            self.buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72, # Top margin
            bottomMargin=72
        )

        story = []

        # --- 1. COVER PAGE ---
        
        # A. Title Section
        story.append(Spacer(1, 0.5*inch)) # Spacing from top margin
        story.append(Paragraph(metadata['title'], self.styles['CoverTitle']))
        story.append(Paragraph(metadata['subtitle'], self.styles['CoverSubtitle']))
        
        # B. Submitted By Section
        story.append(Spacer(1, 0.8*inch))
        story.append(Paragraph("Submitted by", self.styles['SubmittedByLabel']))
        story.append(Paragraph(metadata['name'], self.styles['StudentInfo']))
        story.append(Paragraph(metadata['roll_number'], self.styles['StudentInfo']))
        
        # C. Logo Section
        story.append(Spacer(1, 1.0*inch))
        logo_url = "https://upload.wikimedia.org/wikipedia/en/thumb/6/69/IIT_Madras_Logo.svg/2560px-IIT_Madras_Logo.svg.png"
        logo_path = self.fetch_logo(logo_url)
        
        if logo_path:
            # Aspect ratio of the logo is roughly 1:1 in the circle
            im = Image(logo_path, width=2.8*inch, height=2.8*inch)
            im.hAlign = 'CENTER'
            story.append(im)
        else:
            story.append(Spacer(1, 2.8*inch)) # Placeholder if logo fails

        # D. Institute Details Section (Pushed to bottom via Spacer)
        story.append(Spacer(1, 1.8*inch)) # Adjust this spacer to push text down near footer
        story.append(Paragraph("IITM Online BS Degree Program,", self.styles['InstituteInfo']))
        story.append(Paragraph("Indian Institute of Technology, Madras, Chennai", self.styles['InstituteInfo']))
        story.append(Paragraph("Tamil Nadu, India, 600036", self.styles['InstituteInfo']))

        story.append(PageBreak())

        # --- 2. TABLE OF CONTENTS ---
        story.append(Paragraph("Table of Contents", self.styles['Title']))
        toc = TableOfContents()
        toc.levelStyles = [
            ParagraphStyle(fontName='Times-Bold', fontSize=12, name='TOCHeading1', leftIndent=20, firstLineIndent=-20, spaceBefore=5, leading=12),
            ParagraphStyle(fontName='Times-Roman', fontSize=10, name='TOCHeading2', leftIndent=40, firstLineIndent=-20, spaceBefore=0, leading=12),
        ]
        story.append(toc)
        story.append(PageBreak())

        # --- 3. DYNAMIC CONTENT ---
        for item in content_items:
            if item['type'] == 'heading':
                p = Paragraph(item['text'], self.styles['CustomH1'])
                story.append(p)
            elif item['type'] == 'text':
                p = Paragraph(item['text'], self.styles['BodyText'])
                story.append(p)
                story.append(Spacer(1, 0.1*inch))
            elif item['type'] == 'image':
                if item['file']:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_img:
                        tmp_img.write(item['file'].read())
                        tmp_img_path = tmp_img.name
                    
                    img_flowable = Image(tmp_img_path)
                    
                    # Resize logic
                    avail_width = A4[0] - 144
                    img_width = img_flowable.drawWidth
                    img_height = img_flowable.drawHeight
                    
                    if img_width > avail_width:
                        ratio = avail_width / img_width
                        img_flowable.drawWidth = avail_width
                        img_flowable.drawHeight = img_height * ratio
                        
                    story.append(img_flowable)
                    story.append(Spacer(1, 0.2*inch))

        # --- BUILD ---
        # We use different page numbering functions for the first page vs the rest
        def on_page_layout(canvas, doc):
            page_num = canvas.getPageNumber()
            if page_num == 1:
                # Cover Page: Page "0" logic
                self.draw_cover_footer(canvas, doc)
            else:
                # Content Pages: Standard numbering
                self.draw_content_footer(canvas, doc)

        doc.multiBuild(story, onLaterPages=on_page_layout, onFirstPage=on_page_layout)


# --- STREAMLIT UI ---

st.title("📄 Report Generator")

# --- SIDEBAR: METADATA ---
with st.sidebar:
    st.header("1. Front Page Details")
    title = st.text_input("Main Title", "Maximizing Revenue and Optimizing Inventory Management through Sales Analysis in E-commerce")
    subtitle = st.text_input("Subtitle", "A Final Report for the Secondary BDM Capstone Project")
    name = st.text_input("Student Name", "Anupratee Bharadwaj")
    roll_number = st.text_input("Roll Number", "21f1001850")

# --- MAIN AREA: CONTENT BUILDER ---
st.header("2. Report Content")
st.info("Add sections to your report below. The Table of Contents will be generated automatically based on Headings.")

with st.expander("➕ Add New Content Block", expanded=True):
    col1, col2 = st.columns([1, 3])
    
    with col1:
        block_type = st.selectbox("Block Type", ["Heading", "Paragraph", "Image"])
    
    with col2:
        if block_type == "Heading":
            content_input = st.text_input("Heading Text")
        elif block_type == "Paragraph":
            content_input = st.text_area("Paragraph Text", height=150)
        else:
            content_input = st.file_uploader("Upload Image", type=['png', 'jpg', 'jpeg'], key="content_img")

    if st.button("Add to Report"):
        if block_type == "Image" and content_input:
            st.session_state.content_list.append({
                'type': 'image',
                'file': content_input,
                'text': 'Image'
            })
            st.success("Image added!")
        elif block_type != "Image" and content_input:
            st.session_state.content_list.append({
                'type': 'heading' if block_type == "Heading" else 'text',
                'text': content_input
            })
            st.success(f"{block_type} added!")
        else:
            st.error("Please provide content.")

# Display current content structure
st.divider()
st.subheader("Current Structure Preview")

if not st.session_state.content_list:
    st.write("_No content added yet._")
else:
    for i, item in enumerate(st.session_state.content_list):
        col_prev, col_del = st.columns([8, 1])
        with col_prev:
            if item['type'] == 'heading':
                st.markdown(f"**{i+1}. Heading:** {item['text']}")
            elif item['type'] == 'text':
                st.markdown(f"**Paragraph:** {item['text'][:100]}...")
            elif item['type'] == 'image':
                st.markdown(f"**Image:** {item['file'].name}")
        with col_del:
            if st.button("🗑️", key=f"del_{i}"):
                st.session_state.content_list.pop(i)
                st.rerun()

# --- GENERATE BUTTON ---
st.divider()
if st.button("Generate PDF Report", type="primary"):
    if not st.session_state.content_list:
        st.warning("Please add some content before generating the report.")
    else:
        metadata = {
            'title': title,
            'subtitle': subtitle,
            'name': name,
            'roll_number': roll_number
        }
        
        pdf_buffer = BytesIO()
        generator = PDFGenerator(pdf_buffer)
        
        try:
            # Reset file pointers for images
            for item in st.session_state.content_list:
                if item['type'] == 'image' and item['file']:
                    item['file'].seek(0)
            
            with st.spinner("Fetching resources and generating PDF..."):
                generator.generate(metadata, st.session_state.content_list)
            
            pdf_data = pdf_buffer.getvalue()
            
            st.success("PDF Generated Successfully!")
            
            st.download_button(
                label="📥 Download PDF",
                data=pdf_data,
                file_name=f"{roll_number}_Report.pdf",
                mime="application/pdf"
            )
            
        except Exception as e:
            st.error(f"An error occurred: {e}")