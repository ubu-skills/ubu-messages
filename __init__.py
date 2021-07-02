"""Module for ubu-messages skill
"""
import sys
from adapt.intent import IntentBuilder
from mycroft import MycroftSkill, intent_handler  # type: ignore
from mycroft.audio import wait_while_speaking
from fuzzywuzzy import fuzz, process
sys.path.append("/usr/lib/UBUVoiceAssistant")  # type: ignore
from UBUVoiceAssistant.util import util  # type: ignore


class UbuMessagesSkill(MycroftSkill):
    """Class for the ubu-messages skill"""

    def __init__(self):
        super().__init__()
        self.request_stop = False
        self.webservice = None

    def initialize(self):
        """Gets the initial information for the skill
        """
        self.webservice = util.get_data_from_server()

    @intent_handler(IntentBuilder("UnreadMessagesIntent").require("UnreadMessagesVoc"))
    def recent_messages(self, _):
        """Reads the most recent messages

        Args:
            message: Mycroft message data
        """
        self.request_stop = False
        self.speak_dialog("wait")
        convers = self.webservice.get_conversations_with_messages()
        messages = {}
        msg_from = {}
        user_id = self.webservice.get_user().get_id()
        for conver in convers:
            messages.update(conver.get_messages())
            for msg in conver.get_messages().values():
                if str(msg.get_useridfrom()) != str(user_id):
                    msg_from[msg.get_message_id()] = util.reorder_name(list(
                        conver.get_members().values())[0].get_fullname())
        messagelist = messages.keys()
        if len(msg_from) == 0:
            wait_while_speaking()
            self.speak_dialog("no.messages")
            return
        messagelist = sorted(messagelist, reverse=True)
        print(msg_from, messages)
        wait_while_speaking()
        for num, msg in enumerate(messagelist):
            if msg in msg_from:
                self.speak_dialog("says", data={
                    "person": msg_from[msg],
                    "message": messages[msg].get_clean_text()
                })
                wait_while_speaking()
            if num == 4 or self.request_stop:
                break

    @intent_handler(IntentBuilder("SendMessagePerson").require("EnviarAPersona"))
    def send_message(self, message):
        """The entry point for sending message to a person

        Args:
            message: Mycroft message data
        """
        persona = message.data.get("EnviarAPersona")
        convers = self.webservice.get_conversations()
        id_convers = {}
        for conver in convers:
            id_convers[util.reorder_name(list(conver.get_members().values())[
                                         0].get_fullname()).lower()] = conver.get_conversation_id()
        bests = process.extractBests(persona, list(
            id_convers.keys()), scorer=fuzz.partial_ratio, score_cutoff=75)
        bests_list = [x[0] for x in bests]
        self.select_person(persona, bests_list, id_convers, True)

    def select_person(self, person, person_list, person_id, from_conversations):
        """Prompts the user to select a person from the list

        Args:
            person (str): The name of the person received when launching the skill
            person_list (list[str]): list of similar persons found
            person_id (dict[str, int]): Correspondence between the person's name and the Moodle ID
            from_conversations (bool): True if we are selecting from the list of conversations,
                false if not.
        """
        if len(person_list) == 0:
            self.speak_dialog("nobody.found")
            wait_while_speaking()
            if from_conversations:
                self.message_from_courses(person)
            return
        if len(person_list) > 1:
            person_list.append(self.translate("not.on.list"))
            self.speak_dialog("multiple.matching")
            wait_while_speaking()
            sel = self.ask_selection(person_list, numeric=True)
            if sel is None:
                return
            if sel == self.translate("not.on.list"):
                if from_conversations:
                    self.message_from_courses(person)
                return
            self.speak(sel)
            wait_while_speaking()
            person_list = [sel]
        else:
            yesno = self.ask_yesno("found.one.okay", data={
                                "person": person_list[0]})
            if yesno == "no":
                if from_conversations:
                    self.message_from_courses(person)
                return
            if yesno is None:
                return
        self.send_message_final(person_id[person_list[0]], from_conversations)

    def message_from_courses(self, person):
        """Searchs for users matching the name in a course

        Args:
            person (str): The name of the person we get when launching the skill
        """
        course_name = self.get_response("which.course")
        courses = self.webservice.get_user_courses()
        course_names = {}
        for course in courses:
            course_names[course.get_id()] = course.get_name()
        best_course = process.extractOne(
            course_name, course_names, scorer=fuzz.partial_ratio, score_cutoff=75)
        if best_course is not None:
            participants = self.webservice.get_participants_by_course(best_course)
            id_person = {}
            for participant in participants:
                id_person[util.reorder_name(participant.get_fullname())] = participant.get_id()
            bests = process.extractBests(person, list(
                id_person.keys()), scorer=fuzz.partial_ratio, score_cutoff=75)
            bests_list = [x[0] for x in bests]
            self.select_person(person, bests_list, id_person, False)

    def send_message_final(self, person_id, from_conversations):
        """The final part to send messages

        Args:
            person_id (int): The person or conversation id
            from_conversations (bool): True if we need to reply to a conversation,
                False if we send a message to a new person
        """
        message = self.get_response("say.message")
        yesno = self.ask_yesno("did.i.understood.correctly",
                            data={"message": message})
        if yesno == "yes":
            if from_conversations:
                self.webservice.send_message_to_conversation(message, person_id)
            else:
                self.webservice.send_message_to_user(message, person_id)
            self.speak_dialog("sent")

    def stop(self):
        """Stops the skill
        """
        self.request_stop = True


def create_skill():
    """Creates the ubu-messages skill

    Returns:
        UbuMessagesSkill: The Mycroft Skill to interact with Moodle's messages
    """
    return UbuMessagesSkill()
