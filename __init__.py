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
        for conver in convers:
            messages.update(conver.get_messages())
            for m in conver.get_messages().values():
                msg_from[m.get_message_id()] = util.reorder_name(
                    list(conver.get_members().values())[0].get_fullname())
        l = messages.keys()
        l = sorted(l, reverse=True)
        for n, m in enumerate(l):
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
        if len(bests) == 0:
            self.speak("No he encontrado a nadie.")
        else:
            for (match, score) in bests:
                self.speak(str(match) + str(score))
                wait_while_speaking()
                if match in id_convers:
                    self.speak(id_convers[match])
                    wait_while_speaking()

    def stop(self):
        self.request_stop = True


def create_skill():
    return UbuMessagesSkill()
