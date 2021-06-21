import sys
from adapt.intent import IntentBuilder
from mycroft import MycroftSkill, intent_handler  # type: ignore
from mycroft.audio import wait_while_speaking
from fuzzywuzzy import fuzz, process
sys.path.append("/usr/lib/UBUVoiceAssistant")  # type: ignore
from UBUVoiceAssistant.util import util  # type: ignore


class UbuMessagesSkill(MycroftSkill):

    def __init__(self):
        super().__init__()
        self.request_stop = False

    def initialize(self):
        self.ws = util.get_data_from_server()

    @intent_handler(IntentBuilder("UnreadMessagesIntent").require("UnreadMessagesVoc"))
    def recent_messages(self, message):
        self.request_stop = False
        self.speak("Dame un momento, por favor")
        convers = self.ws.get_conversations_with_messages()
        messages = {}
        msg_from = {}
        user_id = self.ws.get_user().get_id()
        for conver in convers:
            messages.update(conver.get_messages())
            for m in conver.get_messages().values():
                if str(m.get_useridfrom()) != str(user_id):
                    msg_from[m.get_message_id()] = util.reorder_name(list(
                        conver.get_members().values())[0].get_fullname())
        l = messages.keys()
        l = sorted(l, reverse=True)
        print(msg_from, messages)
        for n, m in enumerate(l):
            if m in msg_from:
                self.speak(msg_from[m] + " dice: " + messages[m].get_clean_text())
                wait_while_speaking()
            if n == 4 or self.request_stop:
                break

    @intent_handler(IntentBuilder("SendMessage").require("EnviarAPersona"))
    def send_message(self, message):
        persona = message.data.get("EnviarAPersona")
        convers = self.ws.get_conversations()
        id_convers = {}
        for conver in convers:
            id_convers[util.reorder_name(list(conver.get_members().values())[
                                         0].get_fullname()).lower()] = conver.get_conversation_id()
        bests = process.extractBests(persona, list(id_convers.keys()), scorer=fuzz.partial_ratio, score_cutoff=75)
        bests_list = [x[0] for x in bests]
        self.select_person(persona, bests_list, id_convers, True)

    def select_person(self, person, person_list, person_id, from_conversations):
        if len(person_list) == 0:
            self.speak("No he encontrado a nadie")
            wait_while_speaking()
            if from_conversations:
                self.message_from_courses(person)
            return
        if len(person_list) > 1:
            person_list.append("No está en la lista") # self.translate?
            self.speak("Hay varias posibles coincidencias:")
            wait_while_speaking()
            sel = self.ask_selection(person_list, numeric=True)
            if sel is None:
                return
            if sel == "No está en la lista":
                if from_conversations:
                    self.message_from_courses(person)
                return
            else:
                person_list = [sel]
        else:
            yn = self.ask_yesno("He encontrado a " + person_list[0] + ". ¿Es correcto?")
            if yn == "no":
                if from_conversations:
                    self.message_from_courses(person)
                return
        self.send_message_final(person_id[person_list[0]], from_conversations)
    
    def message_from_courses(self, person):
        course = self.get_response("¿A qué curso va esa persona?")
        courses = self.ws.get_user_courses()
        course_names = {}
        for c in courses:
            course_names[c.get_id()] = c.get_name()
        best_course = process.extractOne(course, course_names, scorer=fuzz.partial_ratio, score_cutoff=75)
        if best_course is not None:
            participants = self.ws.get_participants_by_course(best_course)
            id_person = {}
            for p in participants:
                id_person[util.reorder_name(p.get_fullname())] = p.get_id()
            bests = process.extractBests(person, list(id_person.keys()), scorer=fuzz.partial_ratio, score_cutoff=75)
            bests_list = [x[0] for x in bests]
            self.select_person(person, bests_list, id_person, False)

    def send_message_final(self, person_id, from_conversations):
        message = self.get_response("Dime el mensaje")
        yn = self.ask_yesno("He entendido " + message + "¿Es correcto?")
        if yn != "no":
            if from_conversations:
                self.ws.send_message_to_conversation(message, person_id)
            else:
                self.ws.send_message_to_user(message, person_id)
            self.speak("Okay, he enviado el mensaje")

    def stop(self):
        self.request_stop = True


def create_skill():
    return UbuMessagesSkill()
