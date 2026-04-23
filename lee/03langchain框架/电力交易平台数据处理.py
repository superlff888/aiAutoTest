
from langchain.agents import create_agent
from langchain_community.agent_toolkits import SQLDatabaseToolkit
import os
from dotenv import load_dotenv

from langchain_community.utilities import SQLDatabase
from langchain.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from utils.get_db_tools import getdbtools


load_dotenv()


llm = ChatOpenAI(
    model=os.getenv("OPENAI_MODEL"),
    base_url=os.getenv("OPENAI_BASE_URL"),
    api_key=os.getenv("OPENAI_API_KEY"),     
    temperature=0
    )   


agent = create_agent(
    tools=getdbtools(llm),
    model=llm,
    system_prompt=SystemMessage(content="你是一个SQL专家，协助用户查询数据库中的表结构信息，并生成正确的SQL查询语句") 
)


if __name__ == "__main__":
    human_message=HumanMessage(content="""请帮我执行以下sql，
SELECT
	id,
	transaction_plan_id,
	transaction_cycle,
	NAME,
	JSON_EXTRACT ( trade_detail, '$[0].energy' ) AS 'day_01_energy',
	JSON_EXTRACT ( trade_detail, '$[1].energy' ) AS 'day_02_energy',
	JSON_EXTRACT ( trade_detail, '$[2].energy' ) AS 'day_03_energy',
	JSON_EXTRACT ( trade_detail, '$[3].energy' ) AS 'day_04_energy',
	JSON_EXTRACT ( trade_detail, '$[4].energy' ) AS 'day_05_energy',
	JSON_EXTRACT ( trade_detail, '$[5].energy' ) AS 'day_06_energy',
	JSON_EXTRACT ( trade_detail, '$[6].energy' ) AS 'day_07_energy',
	JSON_EXTRACT ( trade_detail, '$[7].energy' ) AS 'day_08_energy',
	JSON_EXTRACT ( trade_detail, '$[8].energy' ) AS 'day_09_energy',
	JSON_EXTRACT ( trade_detail, '$[9].energy' ) AS 'day_10_energy',
	JSON_EXTRACT ( trade_detail, '$[10].energy' ) AS 'day_11_energy',
	JSON_EXTRACT ( trade_detail, '$[11].energy' ) AS 'day_12_energy',
	JSON_EXTRACT ( trade_detail, '$[12].energy' ) AS 'day_13_energy',
	JSON_EXTRACT ( trade_detail, '$[13].energy' ) AS 'day_14_energy',
	JSON_EXTRACT ( trade_detail, '$[14].energy' ) AS 'day_15_energy',
	JSON_EXTRACT ( trade_detail, '$[15].energy' ) AS 'day_16_energy',
	JSON_EXTRACT ( trade_detail, '$[16].energy' ) AS 'day_17_energy',
	JSON_EXTRACT ( trade_detail, '$[17].energy' ) AS 'day_18_energy',
	JSON_EXTRACT ( trade_detail, '$[18].energy' ) AS 'day_19_energy',
	JSON_EXTRACT ( trade_detail, '$[19].energy' ) AS 'day_20_energy',
	JSON_EXTRACT ( trade_detail, '$[20].energy' ) AS 'day_21_energy',
	JSON_EXTRACT ( trade_detail, '$[21].energy' ) AS 'day_22_energy',
	JSON_EXTRACT ( trade_detail, '$[22].energy' ) AS 'day_23_energy',
	JSON_EXTRACT ( trade_detail, '$[23].energy' ) AS 'day_24_energy',
	JSON_EXTRACT ( trade_detail, '$[24].energy' ) AS 'day_25_energy',
	JSON_EXTRACT ( trade_detail, '$[25].energy' ) AS 'day_26_energy',
	JSON_EXTRACT ( trade_detail, '$[26].energy' ) AS 'day_27_energy',
	JSON_EXTRACT ( trade_detail, '$[27].energy' ) AS 'day_28_energy',
	JSON_EXTRACT ( trade_detail, '$[28].energy' ) AS 'day_29_energy',
	JSON_EXTRACT ( trade_detail, '$[29].energy' ) AS 'day_30_energy',
	JSON_EXTRACT ( trade_detail, '$[30].energy' ) AS 'day_31_energy' 
FROM
	transaction_plan 
WHERE
	trade_center_id = '13' -- 13 四川
	AND NAME LIKE '%【生成】%' 
	AND contact_start_time <= '2026-03-31 00:00:00' AND contact_end_time >= '2026-03-01 00:00:00' 
	AND transaction_cycle IN ( 2, 6 ) 
AND transaction_type = 2;

""")
    
    response = agent.invoke({"messages":[human_message]})
    print(f"==========================\n{response}")
    