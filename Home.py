# app.py
import streamlit as st
import requests
from streamlit_lottie import st_lottie
import streamlit.components.v1 as components
from PIL import Image

# ----------------- Page Configuration ----------------- #
st.set_page_config(page_title='Portfolio', layout="wide", page_icon='🌏')

# ----------------- Load Assets ----------------- #

def load_lottieurl(url: str):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

def load_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Load custom CSS
load_css("style/style.css")

# Loading Lottie animations
lottie_intro = load_lottieurl("https://lottie.host/00517c35-de11-4d81-b606-f0b1e4427991/uexdHHLp7o.json")
python_lottie = load_lottieurl("https://assets6.lottiefiles.com/packages/lf20_2znxgjyt.json")
my_sql_lottie = load_lottieurl("https://assets4.lottiefiles.com/private_files/lf30_w11f2rwn.json")
github_lottie = load_lottieurl("https://assets8.lottiefiles.com/packages/lf20_6HFXXE.json")
docker_lottie = load_lottieurl("https://assets4.lottiefiles.com/private_files/lf30_35uv2spq.json")
js_lottie = load_lottieurl("https://lottie.host/fc1ad1cd-012a-4da2-8a11-0f00da670fb9/GqPujskDlr.json")
html_lottie = load_lottieurl("https://lottie.host/c1982bb5-54ce-492c-b573-a6734a86834e/kdHflDuLEF.json")
# ----------------- Info ----------------- #

# Assuming 'info' is a dictionary defined in 'constant.py' or similar
info = {
    "Pronoun": "He/Him",
    "Name": "Calvin",
    "Full_Name": "Calvin Luo",
    "Intro": "Welcome to my portfolio!",
    "About": "Hey everyone, thanks for stopping by! I'm a GISer with passion in geospatial analytics, geospatial data engineering/visualization, and interactive web mapping. This portfolio page will showcase some of the works I have done.",
    "Photo": "<img src='images/profile.jpeg' width='200' />",
    "Medium": "https://medium.com/@yourusername",
    "Email": "calvinluozhengpei@gmail.com",
    "LinkedIn":"https://www.linkedin.com/in/zhengpei-luo-969787129"
    
}

# ----------------- Gradient Header ----------------- #

def gradient(color1, color2, content1, content2):
    st.markdown(f'''
    <div style="
        text-align:center;
        background-color: black;
        padding: 20px;
        border-radius: 2%;
    ">
        <h1 style="color: white; font-size: 60px;">
            {content1}
        </h1>
        <p style="color: white; font-size: 17px;">
            {content2}
        </p>
    </div>
    ''', unsafe_allow_html=True)

with st.container():
    col1, col2 = st.columns([8, 3])

    full_name = info['Full_Name']
    with col1:
        # Use black background and white text
        gradient('black', 'black', f"Hi, I'm {full_name} 👋", info["Intro"])
        st.write("")  # Adds spacing
        st.markdown(f'<p style="color:black;">{info["About"]}</p>', unsafe_allow_html=True)

    with col2:
        st_lottie(lottie_intro, height=200, key="intro")


# ----------------- Skill Sets ----------------- #

with st.container():
    st.subheader('⚒️ Skills')
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    with col1:
        st_lottie(python_lottie, height=70, width=70, key="python", speed=2.5)
        st.markdown("**Python**")
    with col2:
        st_lottie(my_sql_lottie, height=70, width=70, key="mysql", speed=2.5)
        st.markdown("**MySQL**")
    with col3:
        st_lottie(html_lottie, height=70, width=70, key="html", speed=1)
        st.markdown("**HTML/CSS**")

    
    # Additional skills
    with col1:
        st_lottie(github_lottie, height=50, width=50, key="github", speed=2.5)
        st.markdown("**GitHub**")
    with col2:
        st_lottie(docker_lottie, height=50, width=50, key="docker", speed=2.5)
        st.markdown("**Docker**")
    with col3:
        st_lottie(js_lottie, height=50, width=50, key="js", speed=1)
        st.markdown("**JavaScript**")

    # Additional Skills: ESRI Suite and Open Source Geospatial Tools
    with st.container():
        # First row for ESRI Suite
        st.subheader('🗺️ ESRI Suite')
        st.write("ArcGIS Pro/Map, ArcGIS Online, ArcGIS Enterprise, Web AppBuilder/Experience Builder, StoryMaps, FieldMaps")

        # Second row for Open Source Geospatial Tools
        st.subheader('🌍 Open Source Geospatial Tools/ Others')
        st.write("PostGIS, GDAL, Postgresql, QGIS, GeoServer, Leaflet, Rasterio, Apache Sedona, Apache Airflow , GCP/BigQuery/Terraform")


# ----------------- GIS Portfolio Section ----------------- #

with st.container():
    st.subheader('🌐 GIS Portfolio')
    st.write("""
    Explore some of my GIS projects. Below, you will find links to my static GIS maps hosted on Google Sites and interactive maps created in Streamlit.
    """)

    # Static GIS Maps Portfolio Section with Expander
    with st.expander('📊 Static GIS Maps Portfolio'):
        st.write("""
        You can explore my static GIS maps by visiting the Google Site below:
        """)
        st.markdown(
            """<a href="https://sites.google.com/view/map-portfolio" target="_blank"><em>🔗 Access my GIS Maps Portfolio on Google Site</em></a>""",
            unsafe_allow_html=True
        )
        st.write("(Click on the link for a detailed view of my GIS maps.)")

    # Interactive Map Section with Link to map.py
    st.subheader('🗺️ Interactive Maps')
    st.write("""
    For a more interactive experience, explore my interactive map series:
    """)
    st.markdown(
        """<a href="/map" target="_self"><em>🔗 View Interactive Hong Kong Housing Map</em></a>""",
        unsafe_allow_html=True
    )



# ----------------- Medium Section ----------------- #

embed_rss = {
    'rss': """<div style="overflow-y: scroll; height:500px; background-color:white;"> 
    <div id="retainable-rss-embed" 
        data-rss="https://medium.com/feed/@calvinluozhengpei"
        data-maxcols="3" 
        data-layout="grid"
        data-poststyle="inline" 
        data-readmore="Read the rest" 
        data-buttonclass="btn btn-primary" 
        data-offset="0"
        data-linktarget="_blank"></div></div> 
    <script src="https://www.twilik.com/assets/retainable/rss-embed/retainable-rss-embed.js"></script>"""
}

with st.container():
    st.markdown("""""")
    st.subheader('✍️ Medium')
    st.write("""I recently started writing technical medium blogs to share my passion in the geospatial field. 
         I always have this philosophy: If I can "teach" better, I learn better. As a student of the game, I'm able to find extra
         motivation to learn when I started to author these blogs. Please check them out and give me some feedback if you would like!
         """)
    col1, col2 = st.columns([0.95, 0.05])
    with col1:
        with st.expander('Display my latest posts'):
            components.html(embed_rss['rss'], height=400)

        st.markdown(
            """<a href="https://medium.com/@calvinluozhengpei" target="_blank"><em>🔗 Access to my Medium Profile</em></a>""",
            unsafe_allow_html=True
        )
        st.write("""(Click on the above link for a better view!)""")


# ----------------- Contact Section ----------------- #

# with st.container():
#     st.subheader("📨 Contact Me")
#     col1, col2 = st.columns([0.95, 0.05])
#     with col1:
#         contact_form = f"""
#         <form action="https://formsubmit.co/{info["Email"]}" method="POST">
#             <input type="hidden" name="_captcha" value="false">
#             <input type="text" name="name" placeholder="Your name" required style="width:100%; padding:10px; margin-bottom:10px;">
#             <input type="email" name="email" placeholder="Your email" required style="width:100%; padding:10px; margin-bottom:10px;">
#             <textarea name="message" placeholder="Your message here" required style="width:100%; padding:10px; margin-bottom:10px;"></textarea>
#             <button type="submit" style="background-color:#000395; color:white; padding:10px 20px; border:none; border-radius:5px; cursor:pointer;">Send</button>
#         </form>
#         """
#         st.markdown(contact_form, unsafe_allow_html=True)

# ----------------- Sidebar Content ----------------- #

st.sidebar.markdown(f"""
**Email**: [📧 {info['Email']}](mailto:{info['Email']})  
**Linkedin**: [🔗Linkedin {info['LinkedIn']}](www.linkedin.com/in/zhengpei-luo-969787129)
""")
