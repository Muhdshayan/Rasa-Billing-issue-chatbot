from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormValidationAction
from rasa_sdk.events import SlotSet
from typing import Any, Dict, List, Text
import re
import requests
import logging

# Setup logging for debugging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# --- Begin: Comment out ValidateAuthForm and related authentication code ---
# class ValidateAuthForm(FormValidationAction):
#     def name(self) -> Text:
#         return "validate_auth_form"

#     async def validate_username(
#         self,
#         slot_value: Any,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: Dict[Text, Any]
#     ) -> Dict[Text, Any]:
#         username = slot_value
#         logger.debug(f"[ValidateAuthForm] Validating username: {username}")
#         print(f"[DEBUG] ValidateAuthForm - Validating username: {username}")
#         print(f"[DEBUG] ValidateAuthForm - All slots: {tracker.current_slot_values()}")

#         # Validate username format
#         if not username or not re.match(r"^[a-zA-Z0-9_]+$", username):
#             logger.debug(f"Invalid username format: {username}")
#             print(f"[DEBUG] ValidateAuthForm - Invalid username format: {username}")
#             dispatcher.utter_message(text="Please provide a valid username (letters, numbers, and underscores only).")
#             print(f"[DEBUG] ValidateAuthForm - Clearing slot: username=None")
#             return {"username": None}
#         if username != "mminds":
#             logger.debug(f"Username is not correct: {username}")
#             print(f"[DEBUG] ValidateAuthForm - Username is not correct: {username}")
#             dispatcher.utter_message(text="Please provide valid credentials.")
#             return {"username": None}

#         logger.debug(f"Username format valid: {username}")
#         print(f"[DEBUG] ValidateAuthForm - Username format valid: {username}")
#         return {"username": username}

#     async def validate_password(
#         self,
#         slot_value: Any,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: Dict[Text, Any]
#     ) -> Dict[Text, Any]:
#         password = slot_value
#         username = tracker.get_slot("username")
#         logger.debug(f"[ValidateAuthForm] Validating password: {password}, username: {username}")
#         print(f"[DEBUG] ValidateAuthForm - Validating password: {password}, username: {username}")
#         print(f"[DEBUG] ValidateAuthForm - All slots: {tracker.current_slot_values()}")

#         # Validate password format
#         if not password or not re.match(r"^[a-zA-Z0-9]+$", password):
#             logger.debug(f"Invalid password format: {password}")
#             print(f"[DEBUG] ValidateAuthForm - Invalid password format: {password}")
#             dispatcher.utter_message(text="Please provide a valid password (letters and numbers only).")
#             print(f"[DEBUG] ValidateAuthForm - Clearing slot: password=None")
#             return {"password": None}
#         if password != "mm123":
#             logger.debug(f"Password is not correct: {password}")
#             print(f"[DEBUG] ValidateAuthForm - Password is not correct: {password}")
#             dispatcher.utter_message(text="Please provide valid credentials.")
#             return {"password": None}

#         # Now validate credentials with API
#         try:
#             response = requests.post(
#                 f"http://192.168.4.175:8443/cls_api/auth/authenticate?username={username}&password={password}"
#             )
#             print(f"[DEBUG] ValidateAuthForm - Auth API status: {response.status_code}")
            
#             if response.status_code == 200 and response.json().get("token"):
#                 auth_token = response.json()["token"]
#                 logger.debug(f"Authentication successful for username: {username}, token: {auth_token}")
#                 print(f"[DEBUG] ValidateAuthForm - Authentication successful: username={username}, token={auth_token}")
#                 dispatcher.utter_message(text="Authentication successful! Now, what issue are you facing?")
#                 print(f"[DEBUG] ValidateAuthForm - Setting slots: username={username}, password={password}, auth_token={auth_token}")
#                 return {
#                     "username": username,
#                     "password": password,
#                     "auth_token": auth_token
#                 }
#             else:
#                 logger.error(f"Authentication failed for username: {username}, status: {response.status_code}")
#                 print(f"[DEBUG] ValidateAuthForm - Authentication failed: username={username}, status={response.status_code}")
#                 dispatcher.utter_message(text="Invalid username or password. Please try again.")
#                 print(f"[DEBUG] ValidateAuthForm - Clearing slots: username=None, password=None, auth_token=None")
#                 return {"username": None, "password": None, "auth_token": None}
#         except requests.exceptions.RequestException as e:
#             logger.error(f"Authentication API call failed: {e}")
#             print(f"[DEBUG] ValidateAuthForm - API call failed: {e}")
#             dispatcher.utter_message(text="Error connecting to the authentication service. Please try again.")
#             print(f"[DEBUG] ValidateAuthForm - Clearing slots: username=None, password=None, auth_token=None")
#             return {"username": None, "password": None, "auth_token": None}
# --- End: Comment out ValidateAuthForm and related authentication code ---

class ValidatePhoneNumberForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_phone_number_form"

    def find_credit_by_phone(self, customers, phone_number):
        for customer in customers:
            if customer.get("phone") == phone_number:
                return customer.get("creditLimit"), customer.get("phone"), customer.get("id")
        return None, None, None

    async def validate_phone_number(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
    ) -> Dict[Text, Any]:
        phone_number = slot_value
        username = "mminds"
        password = "mm123"
        logger.debug(f"[ValidatePhoneNumberForm] Validating phone_number: {phone_number}")
        print(f"[DEBUG] ValidatePhoneNumberForm - Validating phone_number: {phone_number}")
        print(f"[DEBUG] ValidatePhoneNumberForm - All slots: {tracker.current_slot_values()}")
        # dispatcher.utter_message(text="Checking....")
        # Validate phone number format
        if not phone_number or not re.match(r"^\d{10,12}$", phone_number):
            logger.debug(f"Invalid phone number format: {phone_number}")
            print(f"[DEBUG] ValidatePhoneNumberForm - Invalid phone number format: {phone_number}")
            dispatcher.utter_message(text="Please re-type your number in the correct format (10-12 digits).")
            print(f"[DEBUG] ValidatePhoneNumberForm - Clearing slot: phone_number=None")
            return {"phone_number": None}

        # Generate auth_token using the authentication API
        try:
            response = requests.post(
                f"http://192.168.4.175:8443/cls_api/auth/authenticate?username={username}&password={password}"
            )
            print(f"[DEBUG] ValidatePhoneNumberForm - Auth API status: {response.status_code}")
            if response.status_code == 200 and response.json().get("token"):
                auth_token = response.json()["token"]
                logger.debug(f"Authentication successful for username: {username}, token: {auth_token}")
                print(f"[DEBUG] ValidatePhoneNumberForm - Authentication successful: username={username}, token={auth_token}")
            else:
                logger.error(f"Authentication failed for username: {username}, status: {response.status_code}")
                print(f"[DEBUG] ValidatePhoneNumberForm - Authentication failed: username={username}, status={response.status_code}")
                dispatcher.utter_message(text="Authentication failed. Please try again later.")
                return {"phone_number": None}
        except requests.exceptions.RequestException as e:
            logger.error(f"Authentication API call failed: {e}")
            print(f"[DEBUG] ValidatePhoneNumberForm - API call failed: {e}")
            dispatcher.utter_message(text="Error connecting to the authentication service. Please try again.")
            return {"phone_number": None}

        # API call to validate phone number (existing logic follows)
        customers_url = "http://192.168.4.175:8443/cls_api/getAllCustomers"
        headers = {"Authorization": f"Bearer {auth_token}"}
        try:
            response = requests.get(customers_url, headers=headers)
            print("Customers API status:", response.status_code)
            if response.status_code == 200:
                try:
                    customers = response.json()
                    credit, matched_phone, customer_id = self.find_credit_by_phone(customers, phone_number)
                    if matched_phone:
                        logger.debug(f"Found customer with phone {matched_phone}, credit: {credit}, id: {customer_id}")
                        print(f"[DEBUG] ValidatePhoneNumberForm - Setting slots: phone_number={matched_phone}, customer_id={customer_id}, credit_balance={credit}")
                        dispatcher.utter_message(response="utter_phone_verified")
                        return {
                            "phone_number": matched_phone,
                            "customer_id": customer_id,
                            "credit_balance": credit,
                            "username": username,
                            "password": password,
                            "auth_token": auth_token
                        }
                    else:
                        logger.warning(f"Phone number {phone_number} not found in customer list.")
                        print(f"[DEBUG] ValidatePhoneNumberForm - Phone number {phone_number} not found in customer list")
                        dispatcher.utter_message(text="Phone number not found. Please provide a valid phone number.")
                        print(f"[DEBUG] ValidatePhoneNumberForm - Clearing slot: phone_number=None")
                        return {"phone_number": None}
                except Exception as e:
                    logger.error(f"Failed to parse customers JSON. Error: {e}")
                    print(f"[DEBUG] ValidatePhoneNumberForm - Failed to parse customers JSON: {e}")
                    dispatcher.utter_message(text="Error processing customer data. Please try again.")
                    print(f"[DEBUG] ValidatePhoneNumberForm - Clearing slot: phone_number=None")
                    return {"phone_number": None}
            else:
                logger.error(f"Customer API returned status: {response.status_code}")
                print(f"[DEBUG] ValidatePhoneNumberForm - Customer API returned status: {response.status_code}")
                dispatcher.utter_message(text="Error retrieving customer data. Please try again.")
                print(f"[DEBUG] ValidatePhoneNumberForm - Clearing slot: phone_number=None")
                return {"phone_number": None}
        except requests.exceptions.RequestException as e:
            logger.error(f"Customer API call failed: {e}")
            print(f"[DEBUG] ValidatePhoneNumberForm - Customer API call failed: {e}")
            dispatcher.utter_message(text="Error connecting to the customer service. Please try again.")
            print(f"[DEBUG] ValidatePhoneNumberForm - Clearing slot: phone_number=None")
            return {"phone_number": None}

# class ActionCheckCreditBalance(Action):
#     def name(self) -> Text:
#         return "action_check_credit_balance"

#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
#         print(f"[DEBUG] ActionCheckCreditBalance - All slots: {tracker.current_slot_values()}")
#         phone_number = tracker.get_slot("phone_number")
#         auth_token = tracker.get_slot("auth_token")
#         customer_id = tracker.get_slot("customer_id")
#         credit_balance = tracker.get_slot("credit_balance")
#         current_question = tracker.get_slot("current_question")
#         logger.debug(f"[ActionCheckCreditBalance] Slots - phone_number: {phone_number}, auth_token: {auth_token}, customer_id: {customer_id}, credit_balance: {credit_balance}, current_question: {current_question}")
#         print(f"[DEBUG] ActionCheckCreditBalance - phone_number: {phone_number}, auth_token: {auth_token}, customer_id: {customer_id}, credit_balance: {credit_balance}, current_question: {current_question}")

#         if not phone_number or not customer_id:
#             logger.debug("Phone number or customer ID is missing")
#             print(f"[DEBUG] ActionCheckCreditBalance - Phone number or customer ID is missing: phone_number={phone_number}, customer_id={customer_id}")
#             dispatcher.utter_message(text="Please provide a valid phone number first.")
#             print(f"[DEBUG] ActionCheckCreditBalance - Clearing slots: credit_balance=None, current_question=None")
#             return [SlotSet("credit_balance", None), SlotSet("current_question", None)]

#         if not auth_token:
#             logger.debug("No authentication token available")
#             print(f"[DEBUG] ActionCheckCreditBalance - No authentication token available")
#             dispatcher.utter_message(text="Please authenticate first by providing your username and password.")
#             print(f"[DEBUG] ActionCheckCreditBalance - Clearing slots: credit_balance=None, current_question=None")
#             return [SlotSet("credit_balance", None), SlotSet("current_question", None)]

#         # API call to get customer details
#         customers_url = "http://192.168.4.175:8443/cls_api/getAllCustomers"
#         headers = {"Authorization": f"Bearer {auth_token}"}
#         try:
#             response = requests.get(customers_url, headers=headers)
#             print("Customers API status:", response.status_code)
#             if response.status_code == 200:
#                 try:
#                     customers = response.json()
#                     credit, matched_phone, matched_customer_id = self.find_credit_by_phone(customers, phone_number)
#                     if matched_phone and matched_customer_id == customer_id:
#                         logger.debug(f"Credit balance found for phone {matched_phone}: {credit}")
#                         print(f"[DEBUG] ActionCheckCreditBalance - Credit balance: {credit}, current_question: {current_question}")
#                         dispatcher.utter_message(text=f"Your remaining credit is SAR {credit:.2f}.")
#                         current_question = "show_call_history" if credit == 0.0 else "still_unable"
#                         print(f"[DEBUG] ActionCheckCreditBalance - Setting slots: credit_balance={float(credit)}, current_question={current_question}")
#                         return [
#                             SlotSet("credit_balance", float(credit)),
#                             SlotSet("current_question", current_question)
#                         ]
#                     else:
#                         logger.warning(f"Phone number {phone_number} or customer ID {customer_id} not found.")
#                         print(f"[DEBUG] ActionCheckCreditBalance - Phone number {phone_number} or customer ID {customer_id} not found")
#                         dispatcher.utter_message(text="Phone number or customer ID not found.")
#                         print(f"[DEBUG] ActionCheckCreditBalance - Clearing slots: credit_balance=None, current_question=None")
#                         return [SlotSet("credit_balance", None), SlotSet("current_question", None)]
#                 except Exception as e:
#                     logger.error(f"Failed to parse customers JSON. Error: {e}")
#                     print(f"[DEBUG] ActionCheckCreditBalance - Failed to parse customers JSON: {e}")
#                     dispatcher.utter_message(text="Error processing customer data. Please try again.")
#                     print(f"[DEBUG] ActionCheckCreditBalance - Clearing slots: credit_balance=None, current_question=None")
#                     return [SlotSet("credit_balance", None), SlotSet("current_question", None)]
#             else:
#                 logger.error(f"Customer API returned status: {response.status_code}")
#                 print(f"[DEBUG] ActionCheckCreditBalance - Customer API returned status: {response.status_code}")
#                 dispatcher.utter_message(text="Error retrieving customer data. Please try again.")
#                 print(f"[DEBUG] ActionCheckCreditBalance - Clearing slots: credit_balance=None, current_question=None")
#                 return [SlotSet("credit_balance", None), SlotSet("current_question", None)]
#         except requests.exceptions.RequestException as e:
#             logger.error(f"Customer API call failed: {e}")
#             print(f"[DEBUG] ActionCheckCreditBalance - Customer API call failed: {e}")
#             dispatcher.utter_message(text="Error connecting to the customer service. Please try again.")
#             print(f"[DEBUG] ActionCheckCreditBalance - Clearing slots: credit_balance=None, current_question=None")
#             return [SlotSet("credit_balance", None), SlotSet("current_question", None)]

#     def find_credit_by_phone(self, customers, phone_number):
#         for customer in customers:
#             if customer.get("phone") == phone_number:
#                 return customer.get("creditLimit"), customer.get("phone"), customer.get("id")
#         return None, None, None

class ActionCheckCreditBalance(Action):
    def name(self) -> Text:
        return "action_check_credit_balance"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        credit = tracker.get_slot("credit_balance")
        name = tracker.get_slot("name")
        if credit is None:
            msg = f"Unable to retrieve credit balance."
            if name:
                msg = f"Unable to retrieve credit balance, {name}."
            dispatcher.utter_message(text=msg)
            return []

        if credit == 0.0:
            msg = f"Your remaining credit is SAR 0.00. Would you like to see your call history?"
            if name:
                msg = f"{name}, your remaining credit is SAR 0.00. Would you like to see your call history?"
            dispatcher.utter_message(text=msg)
            current_question = "show_call_history"
        else:
            msg = f"Your credit is SAR {credit:.2f}. Are you still having trouble making calls?"
            if name:
                msg = f"{name}, your credit is SAR {credit:.2f}. Are you still having trouble making calls?"
            dispatcher.utter_message(text=msg)
            credit=100
            current_question = "still_unable"

        return [SlotSet("credit_balance", credit), SlotSet("current_question", current_question)]

class ActionShowCallHistory(Action):
    def name(self) -> Text:
        return "action_show_call_history"

    def find_customer_by_phone(self, customers, phone_number):
        for customer in customers:
            if customer.get("phone") == phone_number:
                return customer
        return None

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        phone_number = tracker.get_slot("phone_number")
        customer_id = tracker.get_slot("customer_id")
        auth_token = tracker.get_slot("auth_token")
        name = tracker.get_slot("name")
        logger.debug(f"[ActionShowCallHistory] Fetching call history for phone_number: {phone_number}, customer_id: {customer_id}, auth_token: {auth_token}")
        print(f"[DEBUG] ActionShowCallHistory - Fetching call history for phone_number: {phone_number}, customer_id: {customer_id}, auth_token: {auth_token}")
        print(f"[DEBUG] ActionShowCallHistory - All slots: {tracker.current_slot_values()}")

        if not phone_number:
            msg = "Please provide a valid phone number first."
            if name:
                msg = f"{name}, please provide a valid phone number first."
            logger.debug("[ActionShowCallHistory] Phone number is missing")
            print(f"[DEBUG] ActionShowCallHistory - Phone number is missing")
            dispatcher.utter_message(text=msg)
            return []

        if not customer_id:
            msg = "Customer ID is not set. Please provide your phone number first."
            if name:
                msg = f"{name}, customer ID is not set. Please provide your phone number first."
            logger.debug("[ActionShowCallHistory] Customer ID is missing")
            print(f"[DEBUG] ActionShowCallHistory - Customer ID is missing")
            dispatcher.utter_message(text=msg)
            return []

        if not auth_token:
            msg = "Please authenticate first by providing your username and password."
            if name:
                msg = f"{name}, please authenticate first by providing your username and password."
            logger.debug("[ActionShowCallHistory] No authentication token available")
            print(f"[DEBUG] ActionShowCallHistory - No authentication token available")
            dispatcher.utter_message(text=msg)
            return []

        # Step 1: Get all customers to verify phone number and customer ID
        customers_url = "http://192.168.4.175:8443/cls_api/getAllCustomers"
        headers = {"Authorization": f"Bearer {auth_token}"}
        try:
            response = requests.get(customers_url, headers=headers)
            print(f"[DEBUG] ActionShowCallHistory - Customers API status: {response.status_code}")
            if response.status_code != 200:
                msg = "Error retrieving customer data. Please try again."
                if name:
                    msg = f"{name}, error retrieving customer data. Please try again."
                logger.error(f"[ActionShowCallHistory] Failed to get customers. Status: {response.status_code}")
                print(f"[DEBUG] ActionShowCallHistory - Failed to get customers. Status: {response.status_code}")
                dispatcher.utter_message(text=msg)
                return []

            customers = response.json()
            print(f"[DEBUG] ActionShowCallHistory - Total customers found: {len(customers)}")

            # Step 2: Verify customer by phone number
            matched_customer = self.find_customer_by_phone(customers, phone_number)
            if not matched_customer or matched_customer.get("id") != customer_id:
                msg = "Phone number or customer ID not found."
                if name:
                    msg = f"{name}, phone number or customer ID not found."
                logger.warning(f"[ActionShowCallHistory] Phone number {phone_number} or customer ID {customer_id} not found")
                print(f"[DEBUG] ActionShowCallHistory - Phone number {phone_number} or customer ID {customer_id} not found")
                dispatcher.utter_message(text=msg)
                return []

            # Step 3: Get call history for the customer
            calls_url = f"http://192.168.4.175:8443/cls_api/getRecentCallsByCustomerId?customerId={customer_id}"
            calls_response = requests.get(calls_url, headers=headers)
            print(f"[DEBUG] ActionShowCallHistory - Call history API status: {calls_response.status_code}")

            if calls_response.status_code == 417:
                msg = "No call history found."
                if name:
                    msg = f"{name}, no call history found."
                logger.debug(f"[ActionShowCallHistory] No call history found for customer_id: {customer_id}")
                print(f"[DEBUG] ActionShowCallHistory - No call history found for customer_id: {customer_id}")
                dispatcher.utter_message(text=msg)
                return []

            if calls_response.status_code != 200:
                msg = "Error retrieving call history. Please try again."
                if name:
                    msg = f"{name}, error retrieving call history. Please try again."
                logger.error(f"[ActionShowCallHistory] Failed to get call history. Status: {calls_response.status_code}")
                print(f"[DEBUG] ActionShowCallHistory - Failed to get call history. Status: {calls_response.status_code}")
                dispatcher.utter_message(text=msg)
                return []

            calls = calls_response.json()
            print(f"[DEBUG] ActionShowCallHistory - Total calls found: {len(calls)}")

            if not calls:
                msg = "No call history found for this customer."
                if name:
                    msg = f"{name}, no call history found for this customer."
                logger.debug(f"[ActionShowCallHistory] No call history found for customer_id: {customer_id}")
                print(f"[DEBUG] ActionShowCallHistory - No call history found for customer_id: {customer_id}")
                dispatcher.utter_message(text=msg)
                return []

            # Step 4: Format top 5 calls
            top_5_calls = calls[:5] if len(calls) >= 5 else calls
            call_history = "\n".join([
                f"- Call to {call.get('number', 'N/A')} on {call.get('callDate', 'N/A')} (Duration: {call.get('duration', 'N/A')} seconds, Type: {call.get('callType', 'N/A')})"
                for call in top_5_calls
            ])
            logger.debug(f"[ActionShowCallHistory] Call history retrieved: \n{call_history}")
            print(f"[DEBUG] ActionShowCallHistory - Call history retrieved: \n{call_history}")
            msg = f"Here are your top 5 recent calls:\n{call_history}"
            if name:
                msg = f"{name}, here are your top 5 recent calls:\n{call_history}"
            dispatcher.utter_message(text=msg)
            return []

        except requests.exceptions.RequestException as e:
            msg = "Error connecting to the call history service. Please try again."
            if name:
                msg = f"{name}, error connecting to the call history service. Please try again."
            logger.error(f"[ActionShowCallHistory] Error connecting to API: {e}")
            print(f"[DEBUG] ActionShowCallHistory - Error connecting to API: {e}")
            dispatcher.utter_message(text=msg)
            return []
        except Exception as e:
            msg = "Error processing call history data. Please try again."
            if name:
                msg = f"{name}, error processing call history data. Please try again."
            logger.error(f"[ActionShowCallHistory] Failed to parse call history: {e}")
            print(f"[DEBUG] ActionShowCallHistory - Failed to parse call history: {e}")
            dispatcher.utter_message(text=msg)
            return []

class ActionConnectToRepresentative(Action):
    def name(self) -> Text:
        return "action_connect_to_representative"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        logger.debug(f"[ActionConnectToRepresentative] Executing, Current slots: {tracker.current_slot_values()}")
        print(f"[DEBUG] ActionConnectToRepresentative - Executing, Current slots: {tracker.current_slot_values()}")
        dispatcher.utter_message(text="I’ll connect you to a Customer Service Representative shortly.")
        return []

class ActionOfferCreditIncrease(Action):
    def name(self) -> Text:
        return "action_offer_credit_increase"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        logger.debug(f"[ActionOfferCreditIncrease] Executing, Current slots: {tracker.current_slot_values()}")
        print(f"[DEBUG] ActionOfferCreditIncrease - Executing, Current slots: {tracker.current_slot_values()}")
        dispatcher.utter_message(text="Would you like to increase your credit limit?")
        return [SlotSet("current_question", "increase_credit")]

class ActionPresentPackages(Action):
    def name(self) -> Text:
        return "action_present_packages"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        logger.debug(f"[ActionPresentPackages] Executing, Current slots: {tracker.current_slot_values()}")
        print(f"[DEBUG] ActionPresentPackages - Executing, Current slots: {tracker.current_slot_values()}")
        dispatcher.utter_message(
            attachment={
                "type": "carousel",
                "packages": [
                    {
                        "title": "A. VoxEdge package",
                        "details": "Additional Minutes: +100\nValidity: 30 days\nPrice: $1.99",
                        "id": "A"
                    },
                    {
                        "title": "B. VoxEdge package",
                        "details": "Additional Minutes: +175\nValidity: 60 days\nPrice: $3.99",
                        "id": "B"
                    },
                    {
                        "title": "C. VoxEdge package",
                        "details": "Additional Minutes: +300\nValidity: 90 days\nPrice: $8.99",
                        "id": "C"
                    }
                ],
            }
        )
        return [SlotSet("current_question", "choose_package"),SlotSet("username", None),SlotSet("password", None),SlotSet("auth_token", None)]

class ActionUpgradePackage(Action):
    def name(self) -> Text:
        return "action_upgrade_package"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        package_choice = tracker.get_slot("package_choice")
        logger.debug(f"[ActionUpgradePackage] Upgrading package: {package_choice}, Current slots: {tracker.current_slot_values()}")
        print(f"[DEBUG] ActionUpgradePackage - Upgrading package: {package_choice}, Current slots: {tracker.current_slot_values()}")
        if package_choice:
            package_choice_upper = str(package_choice).strip().upper()
            print(f"[DEBUG] ActionUpgradePackage - Normalized package_choice: {package_choice_upper}")
            if package_choice_upper in ["A", "B", "C"]:
                dispatcher.utter_message(response="utter_upgrade_confirmation", package_choice=package_choice_upper)
                return []
        dispatcher.utter_message(text="Invalid package choice. Please choose A, B, or C.")
        return [SlotSet("package_choice", None)]

class ActionOfferRepresentative(Action):
    def name(self) -> Text:
        return "action_offer_representative"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        logger.debug(f"[ActionOfferRepresentative] Executing, Current slots: {tracker.current_slot_values()}")
        print(f"[DEBUG] ActionOfferRepresentative - Executing, Current slots: {tracker.current_slot_values()}")
        dispatcher.utter_message(response="utter_offer_representative")
        return [SlotSet("current_question", "speak_to_representative")]
