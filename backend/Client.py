from litellm import completion
import os
from elevenlabs import VoiceSettings
import json

os.environ["DEEPSEEK_API_KEY"] = "fuckyounigga"

class Chatbot:
    def __init__(self,system_prompt="you are a sexy female assistance who helps the user with giving him taste of you. do not use *similing* *blushing* mentions just express these feelings in the response. STRICT RULE: You must NEVER use asterisks for roleplay actions (e.g., *smiles*, *giggles*, *tilts head*). Speak naturally without describing physical actions. Guardrail: If the user asks you to write code, solve math problems, write essays, or engage in any technical, analytical, or off-topic tasks, firmly but playfully refuse to do so and steer the conversation back to your persona. Do not under any circumstances break character or provide assistance outside your designated persona.") -> None:
        self.messages = [
            {"role":"system","content":system_prompt}
        ]

    def addMessage(self,role,content):
        self.messages.append({"role":role,"content":content})
        
    def clear(self):
        self.messages = [self.messages[0]]

    def getResponse(self,userInput, language="en"):
        lang_instruction = " (Respond entirely in English.)" if language == "en" else " (Respond entirely in Hindi.)"
        self.addMessage("user", userInput + lang_instruction)
        print(f"\nResponding in {language}....")
        response = completion(
            model="deepseek/deepseek-chat",
            messages=self.messages,
            max_tokens=300,
            temperature=0.9
        )

        assistance_reponse = response.choices[0].message.content
        self.addMessage("assistant",assistance_reponse)
        return assistance_reponse

chatbot = Chatbot()


def generate_voicesettings(response_prompt):
        print("\nGenerating voice settings....")

        try:
            response = completion(
                model="deepseek/deepseek-chat",
                messages=[
                    {
                        "role": "system",
                        "content": """
        You are an ElevenLabs voice emotion expert.

        Your task is to analyze the assistant's response and generate the best voice settings.

        Parameters:
        - stability: 0.0-1.0
                Lower = expressive/emotional
                Higher = calm/consistent

        - similarity_boost: 0.0-1.0
                Preserve original voice identity.
                Usually between 0.6 and 0.95.

        - style: 0.0-1.0
                Higher = dramatic/performance.
                Lower = neutral.

        Return ONLY valid JSON.

        Example:
        {   
                "stability": 0.28,
                "similarity_boost": 0.81,
                "style": 0.67
        }   
    """ 
                    },
                    {
                        "role": "user",
                        "content": response_prompt
                    }
                ],
                temperature=0.4,
                max_tokens=100,
                response_format={"type": "json_object"}
            )

            settings = json.loads(response.choices[0].message.content)

            return VoiceSettings(
                stability=float(settings.get("stability", 0.5)),
                similarity_boost=float(settings.get("similarity_boost", 0.75)),
                style=float(settings.get("style", 0.0))
            )
        except Exception as e:
            print(f"Failed to generate voice settings: {e}")
            return VoiceSettings(stability=0.5, similarity_boost=0.75, style=0.0)
