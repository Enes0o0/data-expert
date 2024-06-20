import streamlit as st
import openai
import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
from crewai import Agent, Task, Crew, Process
from crewai_tools import WebsiteSearchTool, SerperDevTool
from langchain_community.chat_models import ChatOpenAI
from langchain.memory import ChatMessageHistory
from langchain.memory import StreamlitChatMessageHistory
from langchain.schema import HumanMessage, AIMessage
import constants

st.subheader("Tom's Hardware GPU Bilgilerini Excel'e Aktarma")


api_key = constants.OPENAI_API_KEY
serper_api_key = constants.SERPER_API_KEY

os.environ['OPENAI_API_KEY'] = api_key
os.environ['SERPER_API_KEY'] = serper_api_key

llm = ChatOpenAI(
    model_name="gpt-3.5-turbo-0125",
    openai_api_key=api_key
)


website_search_tool = WebsiteSearchTool()
serper_tool = SerperDevTool()

if 'history' not in st.session_state:
    st.session_state['history'] = ChatMessageHistory()

chat_memory = StreamlitChatMessageHistory()


Data_agent = Agent(
    role='Veri Analisti',
    goal='Tom\'s Hardware sitesindeki GPU tablosu bilgilerini çek ve Excel dosyasına aktar',
    backstory='Sen teknoloji sektörü verileri konusunda uzmanlaşmış bir veri analistisın',
    verbose=True,
    allow_delegation=False,
    llm=llm,
    tools=[website_search_tool, serper_tool],
    memory=chat_memory  
)

prompt = st.text_area("Tom's Hardware sitesindeki GPU tablosunu inceleyerek hangi konuyu araştırmamı istersiniz?", key="prompt")

def scrape_toms_hardware():
    url = "https://www.tomshardware.com/reviews/gpu-hierarchy,4388.html"
    try:
        response = requests.get(url, verify=True)  # SSL doğrulamasını etkinleştirmek için
        response.raise_for_status()  
    except requests.exceptions.RequestException as e:
        st.error(f"Veri çekme hatası: {e}")
        return None

    soup = BeautifulSoup(response.content, "html.parser")

    data = []
    table = soup.find("table")

    if table is None:
        st.error("Tablo bulunamadı. Sayfa yapısı değişmiş olabilir.")
        return None

    # Başlıkları belirlendiği gibi ayarlıyoruz
    headers = ["Graphics Card", "Lowest Price", "1080p Ultra", "1080p Medium", "1440p Ultra", "4K Ultra", "Specifications"]

    rows = table.find_all("tr")[1:]  

    for row in rows:
        columns = row.find_all("td")
        if len(columns) >= 7:  
            data.append([
                columns[0].text.strip(),  # Graphics Card
                columns[1].text.strip(),  # Lowest Price
                columns[2].text.strip(),  # 1080p Ultra
                columns[3].text.strip(),  # 1080p Medium
                columns[4].text.strip(),  # 1440p Ultra
                columns[5].text.strip(),  # 4K Ultra
                columns[6].text.strip()   # Specifications
            ])

    if not data:
        st.error("Tablodan veri çekilemedi. Veri yok veya sayfa yapısı değişmiş olabilir.")
        return None

    df = pd.DataFrame(data, columns=headers)
    return df

if prompt:
    improved_prompt = f"""
    Sen yüksek kaliteli verileri excel tablolarına organize etmede uzmanlaşmış bir veri analistisin. Sana verdiğim bilgilerle, Tom's Hardware sitesindeki GPU tablosu verilerini almanı ve bunları temiz, düzenli ve analiz edilebilir bir biçimde Excel dosyasına aktarmanı istiyorum.

    Lütfen aşağıdaki kriterlere uygun bir araştırma yap:
    - Tablodaki tüm verileri çek ve sırasıyla uygun başlıklar altında organize et: 'Graphics Card', 'Lowest Price', '1080p Ultra', '1080p Medium', '1440p Ultra', '4K Ultra', 'Specifications'.
    - Verileri çekmeden önce, verilerin güncel ve doğru olduğundan emin ol.
    - Eğer herhangi bir veri eksik veya hatalı görünüyorsa, bu durumları not al ve kullanıcının bilgilendirilmesini sağla.
    - Verileri Excel'e aktardığında, her sütunun doğru formatta ve okunabilir olduğundan emin ol.
    - Kullanıcı için verilerin ne anlama geldiği ve nasıl kullanılabileceği hakkında kısa bir özet yaz.

    {prompt}
    """

    task = Task(description=improved_prompt, agent=Data_agent, expected_output="Veri analiz sonuçları")

    crew = Crew(
        agents=[Data_agent],
        tasks=[task],
        verbose=2,
        process=Process.sequential
    )

    if st.button("Oluştur"):
        with st.spinner("Yanıt oluşturuluyor..."):
            crew.kickoff()

            
            if hasattr(task, 'output') and task.output:
                result = task.output.exported_output if hasattr(task.output, 'exported_output') else "Çıktı alınamadı."
            else:
                result = "Çıktı alınamadı."

            
            st.session_state.history.add_user_message(prompt)
            st.session_state.history.add_ai_message(result)

            
            st.markdown("### Tom's Hardware GPU Veri Analiz Sonuçları:")
            st.write(result)

            
            df = scrape_toms_hardware()
            if df is not None:
                df.to_excel("toms_hardware_gpu_verileri.xlsx", index=False)
                st.markdown("### Tom's Hardware GPU Verileri Excel Dosyası:")
                st.download_button(label="Excel dosyasını indir", data=open("toms_hardware_gpu_verileri.xlsx", "rb").read(), file_name="toms_hardware_gpu_verileri.xlsx")
            else:
                st.error("Veriler çekilemedi veya tablo bulunamadı.")
