# agents/summarizer.py
import asyncio
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)

from state import NewsState
from config import Config


class NewsSummarizerAgent:
    """뉴스를 요약하는 에이전트"""

    def __init__(self, llm: ChatOpenAI):
        self.name = "News Summarizer"
        self.llm = llm
        self.system_prompt = """당신은 전문 뉴스 요약 전문가입니다. 
        주어진 뉴스를 핵심만 간결하게 2-3문장으로 요약해주세요.
        - 사실만을 전달하고 추측은 피하세요
        - 중요한 숫자나 날짜는 포함하세요
        - 명확하고 이해하기 쉽게 작성하세요"""

        self.prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessagePromptTemplate.from_template(self.system_prompt),
                HumanMessagePromptTemplate.from_template(
                    "제목: {title}\n내용: {content}\n\n위 뉴스를 2-3문장으로 요약해주세요:"
                ),
            ]
        )

    async def summarize_single_news(self, news_item: Dict[str, Any]) -> Dict[str, Any]:
        """단일 뉴스 요약"""
        try:
            # 내용이 너무 짧으면 원본 사용
            if len(news_item["summary"]) < 50:
                return {**news_item, "ai_summary": news_item["summary"]}

            chain = self.prompt | self.llm
            summary_response = await chain.ainvoke(
                {
                    "title": news_item["title"],
                    "content": news_item["raw_summary"][:500],
                }
            )

            summary = summary_response.content.strip()

            return {
                **news_item,
                "ai_summary": summary if summary else news_item["summary"],
            }

        except Exception as e:
            print(
                f"  [{self.name}] 요약 오류 (ID: {news_item['id']}): {str(e)[:50]}..."
            )
            return {
                **news_item,
                "ai_summary": news_item["summary"],  # 오류 시 원본 사용
            }

    async def summarize_news(self, state: NewsState) -> NewsState:
        """모든 뉴스를 비동기로 요약"""
        print(f"\n[{self.name}] 뉴스 요약 시작...")

        # 배치 처리
        batch_size = Config.BATCH_SIZE
        summarized_news = []
        total_news = len(state.raw_news)

        for i in range(0, total_news, batch_size):
            batch = state.raw_news[i : i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total_news + batch_size - 1) // batch_size

            print(f"  배치 {batch_num}/{total_batches} 처리 중...")

            tasks = [self.summarize_single_news(news) for news in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # 예외 처리
            for idx, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    print(f"    뉴스 {batch[idx]['id']} 요약 실패")
                    summarized_news.append(
                        {**batch[idx], "ai_summary": batch[idx]["summary"]}
                    )
                else:
                    summarized_news.append(result)

        state.summarized_news = summarized_news
        state.messages.append(
            AIMessage(content=f"{len(summarized_news)}개의 뉴스 요약을 완료했습니다.")
        )

        print(f"[{self.name}] 요약 완료\n")
        return state
