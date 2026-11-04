import asyncio

from src.database import engine
from src.session_service import SessionService


SESSION_TITLE = "AI ML Learning"
DOCUMENT_NAME = "sample.pdf"


async def main():

    service = SessionService()


    # ---------------------------------------------
    # CREATE SESSION
    # ---------------------------------------------

    chat_session = await service.create_session(
        title=SESSION_TITLE
    )


    # ---------------------------------------------
    # ATTACH DOCUMENT
    # ---------------------------------------------

    document = await service.attach_document_by_name(
        session_id=chat_session.id,
        document_name=DOCUMENT_NAME
    )


    print(
        "\n"
        + "=" * 70
    )

    print(
        "SESSION CREATED"
    )

    print(
        "=" * 70
    )


    print(
        "Session ID:",
        chat_session.id
    )

    print(
        "Title:",
        chat_session.title
    )

    print(
        "Attached document:",
        document.name
    )

    print(
        "Document ID:",
        document.id
    )


    await engine.dispose()


if __name__ == "__main__":

    asyncio.run(
        main()
    )