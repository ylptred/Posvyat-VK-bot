import json
import logging

import vk_api.vk_api
from sqlalchemy.orm import Session

from app.vk_tools.google.spreadsheet_parser.spreadsheet_parser import get_data
from app.create_db import Sendings, Orgs, Groups, Command, Guests, Info
from app.vk_tools.utils.make_domain import make_domain
from app.vk_tools.utils.upload import upload_photo, upload_pdf_doc


def get_init_data(
        vk: vk_api.vk_api.VkApiMethod,
        session: Session,
        spreadsheet_id: str,
        creds_file_name: str,
        token_file_name: str,
) -> None:
    # Подключение логов
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    logger = logging.getLogger(__name__)

    spreadsheet = get_data(
        spreadsheet_id,
        creds_file_name,
        token_file_name
    )

    # getting info about guests' groups
    groups_sheet = spreadsheet['Levels']
    existing_groups = [group.group_info for group in session.query(Groups).all()]

    for i in range(1, len(groups_sheet)):
        group_info = groups_sheet[i][1]

        if group_info not in existing_groups:
            group_num = groups_sheet[i][0]

            session.add(
                Groups(
                    group_num=group_num,
                    group_info=group_info
                )
            )

    # getting info about commands for calling
    commands_sheet = spreadsheet['Commands']
    existing_commands = [command.name for command in session.query(Command).all()]

    for i in range(1, len(commands_sheet)):
        name = commands_sheet[i][0]

        if name not in existing_commands:
            arguments = commands_sheet[i][1]
            desc = commands_sheet[i][2]
            admin = True if commands_sheet[i][3] == '1' else False

            session.add(
                Command(
                    name=name,
                    arguments=arguments,
                    desc=desc,
                    admin=admin
                )
            )

    # getting info about mailings
    sendings_sheet = spreadsheet['Sendings']
    existing_sengings = [sending.mail_name for sending in session.query(Sendings).all()]

    for i in range(1, len(sendings_sheet)):
        name = sendings_sheet[i][0]

        if name not in existing_sengings:

            text = sendings_sheet[i][1]
            groups = sendings_sheet[i][2]
            send_time = sendings_sheet[i][3]
            pics = sendings_sheet[i][4]
            video = sendings_sheet[i][5]
            reposts = sendings_sheet[i][6]
            docs = sendings_sheet[i][7]

            pic_ids = []
            if pics:
                pics_json = f'[{pics}]'

                for pic in json.loads(pics_json):
                    pic_id = upload_photo(
                        vk=vk,
                        photo_id=pic,
                        image_file_path=f'./app/vk_tools/google/spreadsheet_parser/attachments/{pic}.png'
                    )

                    if len(pic_id) != 0:
                        pic_ids.append(pic_id)

            logger.info(f'Pics: {pic_ids}')

            doc_ids = []
            if docs:
                docs_json = f'[{docs}]'

                for doc in json.loads(docs_json):
                    doc_id = upload_pdf_doc(
                        vk=vk,
                        doc_id=doc,
                        doc_file_path=f'./app/vk_tools/google/spreadsheet_parser/attachments/{doc}.pdf'
                    )

                    if len(doc_id) != 0:
                        doc_ids.append(doc_id)

            logger.info(f'Docs: {doc_ids}')

            session.add(
                Sendings(
                    mail_name=name,
                    send_time=send_time,
                    groups=groups,
                    text=text,
                    pics=json.dumps(pic_ids) if len(pic_ids) > 0 else '[]',
                    video=f'[{video}]' if video else '[]',
                    reposts=f'[{reposts}]' if reposts else '[]',
                    docs=json.dumps(doc_ids) if docs else '[]'
                )
            )

    # getting info about users with admin rights
    organizers_sheet = spreadsheet['Organizers']
    existing_organizers = [organizer.chat_id for organizer in session.query(Orgs).all()]

    for i in range(1, len(organizers_sheet)):
        chat_id = int(organizers_sheet[i][0])

        if chat_id not in existing_organizers:
            surname = organizers_sheet[i][1]
            name = organizers_sheet[i][2]
            patronymic = organizers_sheet[i][3]
            vk_link = make_domain(organizers_sheet[i][4])
            groups = organizers_sheet[i][5]

            session.add(
                Orgs(
                    chat_id=chat_id,
                    name=name,
                    surname=surname,
                    patronymic=patronymic,
                    vk_link=vk_link,
                    groups=f'[{groups}]'
                )
            )

    # getting info about participants
    guests_sheet = spreadsheet['Guests']
    existing_guests = session.query(Guests).all()

    for i in range(1, len(guests_sheet)):
        vk_link = make_domain(guests_sheet[i][5])

        for guest in existing_guests:

            if vk_link == guest.vk_link:
                guest.surname = guests_sheet[i][0]
                guest.name = guests_sheet[i][1]
                guest.patronymic = guests_sheet[i][2]
                guest.phone_number = guests_sheet[i][3]
                guest.tag = guests_sheet[i][4]

                groups = json.loads(f'[{guests_sheet[i][6]}]') if guests_sheet[i][6] else None
                guest_groups = json.loads(guest.groups)

                if groups and len(groups) > len(guest_groups):
                    guest.groups = f'[{guests_sheet[i][6]}]'

    info_sheet = spreadsheet['Info']
    existing_info = [information.question for information in session.query(Info).all()]

    for i in range (1, len(info_sheet)):

        info_question = info_sheet[i][0]

        if info_question not in existing_info:
            info_answer = info_sheet[i][1]

            session.add(
                Info(
                    question=info_question,
                    answer=info_answer
                )
            )


    session.commit()
