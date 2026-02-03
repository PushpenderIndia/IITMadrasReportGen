import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.units import inch
from io import BytesIO
import tempfile
import os
from bs4 import BeautifulSoup
from streamlit_quill import st_quill

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="PDF Report Generator", layout="wide")

# --- SESSION STATE MANAGEMENT ---
if 'content_list' not in st.session_state:
    st.session_state.content_list = []

# --- HELPER FUNCTIONS ---

def clean_html_for_reportlab(html_content):
    """
    Quill returns standard HTML (<b>, <i>, <p>). ReportLab uses a limited XML-like markup.
    This function bridges the gap.
    """
    if not html_content:
        return ""
    soup = BeautifulSoup(html_content, "html.parser")
    
    clean_text = ""
    for element in soup.recursiveChildGenerator():
        if element.name is None:
            clean_text += element
        elif element.name == 'strong' or element.name == 'b':
            clean_text += f"<b>{element.text}</b>"
        elif element.name == 'em' or element.name == 'i':
            clean_text += f"<i>{element.text}</i>"
        elif element.name == 'u':
            clean_text += f"<u>{element.text}</u>"
        elif element.name == 'br':
            clean_text += "<br/>"
        elif element.name == 'p':
            if clean_text: 
                clean_text += "<br/>"
    
    return clean_text

class PDFGenerator:
    def __init__(self, buffer):
        self.buffer = buffer
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()

    def setup_custom_styles(self):
        # Using Times-Roman family to match the screenshot
        self.styles.add(ParagraphStyle(
            name='CoverTitle', parent=self.styles['Title'], fontSize=18, leading=22,
            alignment=TA_CENTER, spaceAfter=12, fontName='Times-Bold'
        ))
        self.styles.add(ParagraphStyle(
            name='CoverSubtitle', parent=self.styles['Normal'], fontSize=14, leading=18,
            alignment=TA_CENTER, spaceAfter=40, fontName='Times-Roman'
        ))
        self.styles.add(ParagraphStyle(
            name='SubmittedByLabel', parent=self.styles['Normal'], fontSize=12, leading=16,
            alignment=TA_CENTER, fontName='Times-Bold', spaceAfter=6
        ))
        self.styles.add(ParagraphStyle(
            name='StudentInfo', parent=self.styles['Normal'], fontSize=12, leading=18,
            alignment=TA_CENTER, fontName='Times-Roman'
        ))
        self.styles.add(ParagraphStyle(
            name='InstituteInfo', parent=self.styles['Normal'], fontSize=12, leading=16,
            alignment=TA_CENTER, fontName='Times-Roman'
        ))
        self.styles.add(ParagraphStyle(
            name='CustomH1', parent=self.styles['Heading1'], fontSize=16, leading=20,
            spaceBefore=20, spaceAfter=10, fontName='Times-Bold'
        ))
        
        # Override BodyText
        self.styles['BodyText'].fontSize = 11
        self.styles['BodyText'].leading = 14
        self.styles['BodyText'].alignment = TA_JUSTIFY
        self.styles['BodyText'].fontName = 'Times-Roman'

    def draw_cover_footer(self, canvas, doc):
        canvas.saveState()
        canvas.setFont('Times-Roman', 11)
        canvas.drawCentredString(A4[0] / 2.0, 0.75 * inch, "0")
        canvas.restoreState()

    def draw_content_footer(self, canvas, doc):
        page_num = canvas.getPageNumber()
        canvas.saveState()
        canvas.setFont('Times-Roman', 10)
        canvas.drawCentredString(A4[0] / 2.0, 0.5 * inch, str(page_num))
        canvas.restoreState()

    def generate(self, metadata, content_items):
        doc = SimpleDocTemplate(
            self.buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72
        )
        story = []

        # --- COVER PAGE ---
        story.append(Spacer(1, 0.5*inch))
        story.append(Paragraph(metadata['title'], self.styles['CoverTitle']))
        story.append(Paragraph(metadata['subtitle'], self.styles['CoverSubtitle']))
        
        story.append(Spacer(1, 0.8*inch))
        story.append(Paragraph("Submitted by", self.styles['SubmittedByLabel']))
        story.append(Paragraph(metadata['name'], self.styles['StudentInfo']))
        story.append(Paragraph(metadata['roll_number'], self.styles['StudentInfo']))
        
        story.append(Spacer(1, 1.0*inch))
        
        # --- LOCAL LOGO LOGIC ---
        logo_filename = "IIT_Madras_Logo.png"
        if os.path.exists(logo_filename):
            im = Image(logo_filename, width=1.8*inch, height=1.8*inch)
            im.hAlign = 'CENTER'
            story.append(im)
        else:
            # Fallback if file is missing
            story.append(Paragraph("(Logo file not found)", self.styles['StudentInfo']))
            story.append(Spacer(1, 1.8*inch))

        story.append(Spacer(1, 1.8*inch))
        story.append(Paragraph("IITM Online BS Degree Program,", self.styles['InstituteInfo']))
        story.append(Paragraph("Indian Institute of Technology, Madras, Chennai", self.styles['InstituteInfo']))
        story.append(Paragraph("Tamil Nadu, India, 600036", self.styles['InstituteInfo']))
        story.append(PageBreak())

        # --- TOC ---
        story.append(Paragraph("Table of Contents", self.styles['Title']))
        toc = TableOfContents()
        toc.levelStyles = [
            ParagraphStyle(fontName='Times-Bold', fontSize=12, name='TOCHeading1', leftIndent=20, firstLineIndent=-20, spaceBefore=5, leading=12),
            ParagraphStyle(fontName='Times-Roman', fontSize=10, name='TOCHeading2', leftIndent=40, firstLineIndent=-20, spaceBefore=0, leading=12),
        ]
        story.append(toc)
        story.append(PageBreak())

        # --- DYNAMIC CONTENT ---
        for item in content_items:
            if item['type'] == 'heading':
                story.append(Paragraph(item['text'], self.styles['CustomH1']))
            elif item['type'] == 'text':
                clean_xml = clean_html_for_reportlab(item['text'])
                story.append(Paragraph(clean_xml, self.styles['BodyText']))
                story.append(Spacer(1, 0.1*inch))
            elif item['type'] == 'image':
                if item['file']:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_img:
                        tmp_img.write(item['file'].read())
                        tmp_img_path = tmp_img.name
                    
                    img = Image(tmp_img_path)
                    avail_width = A4[0] - 144
                    if img.drawWidth > avail_width:
                        ratio = avail_width / img.drawWidth
                        img.drawWidth = avail_width
                        img.drawHeight = img.drawHeight * ratio
                    story.append(img)
                    story.append(Spacer(1, 0.2*inch))

        def on_page_layout(canvas, doc):
            page_num = canvas.getPageNumber()
            if page_num == 1:
                self.draw_cover_footer(canvas, doc)
            else:
                self.draw_content_footer(canvas, doc)

        doc.multiBuild(story, onLaterPages=on_page_layout, onFirstPage=on_page_layout)

# --- UI ---

st.title("📄 Report Generator")

with st.sidebar:
    st.header("1. Front Page Details")
    title = st.text_input("Main Title", "Maximizing Revenue and Optimizing Inventory Management through Sales Analysis in E-commerce")
    subtitle = st.text_input("Subtitle", "A Final Report for the Secondary BDM Capstone Project")
    name = st.text_input("Student Name", "Pushpender Singh")
    roll_number = st.text_input("Roll Number", "21f1001850")

st.header("2. Report Content")
st.info("Add sections. For Paragraphs, you can use Bold, Italics, and Underline.")

with st.expander("➕ Add New Content Block", expanded=True):
    col1, col2 = st.columns([1, 3])
    
    with col1:
        block_type = st.selectbox("Block Type", ["Heading", "Paragraph", "Image"])
    
    with col2:
        if block_type == "Heading":
            content_input = st.text_input("Heading Text")
        elif block_type == "Paragraph":
            content_input = st_quill(placeholder="Write your text here...", key="quill_editor")
        else:
            content_input = st.file_uploader("Upload Image", type=['png', 'jpg', 'jpeg'], key="content_img")

    if st.button("Add to Report"):
        if block_type == "Image" and content_input:
            st.session_state.content_list.append({
                'type': 'image', 'file': content_input, 'text': 'Image'
            })
            st.success("Image added!")
            st.rerun()
        elif block_type != "Image" and content_input:
            st.session_state.content_list.append({
                'type': 'heading' if block_type == "Heading" else 'text',
                'text': content_input
            })
            st.success(f"{block_type} added!")
            st.rerun()
        else:
            st.error("Please provide content.")

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
                st.caption(f"Paragraph (Rich Text): {item['text'][:100]}...")
            elif item['type'] == 'image':
                st.markdown(f"**Image:** {item['file'].name}")
        with col_del:
            if st.button("🗑️", key=f"del_{i}"):
                st.session_state.content_list.pop(i)
                st.rerun()

st.divider()
if st.button("Generate PDF Report", type="primary"):
    if not st.session_state.content_list:
        st.warning("Please add some content.")
    else:
        metadata = {'title': title, 'subtitle': subtitle, 'name': name, 'roll_number': roll_number}
        pdf_buffer = BytesIO()
        generator = PDFGenerator(pdf_buffer)
        
        try:
            for item in st.session_state.content_list:
                if item['type'] == 'image' and item['file']:
                    item['file'].seek(0)
            
            with st.spinner("Generating PDF..."):
                generator.generate(metadata, st.session_state.content_list)
            
            st.success("Success!")
            st.download_button(label="📥 Download PDF", data=pdf_buffer.getvalue(), file_name=f"{roll_number}_Report.pdf", mime="application/pdf")
        except Exception as e:
            st.error(f"Error: {e}")