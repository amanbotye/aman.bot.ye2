from enum import StrEnum
class State(StrEnum):
    IDLE='idle'; NAME_INPUT='name_input'; COMPANY_SELECTION='company_selection'; PHONE_INPUT='phone_input'; PHONE_CONFIRMATION='phone_confirmation'
    PHONE_SELECT='phone_select'; PAYMENT_METHOD='payment_method'; PAYMENT_REFERENCE='payment_reference'; PAYMENT_PROOF='payment_proof'; PAYMENT_SUBMITTED='payment_submitted'
    SUPPORT_SUBJECT='support_subject'; SUPPORT_MESSAGE='support_message'; SUPPORT_TICKET_SELECT='support_ticket_select'; SUPPORT_REPLY='support_reply'
    ADMIN_MENU='admin_menu'; ADMIN_REJECT_REASON='admin_reject_reason'; ADMIN_SETTINGS_VALUE='admin_settings_value'; ADMIN_SETTINGS_CONFIRM='admin_settings_confirm'; ADMIN_SEARCH='admin_search'; ADMIN_PAYMENT_SELECT='admin_payment_select'; ADMIN_TICKET_SELECT='admin_ticket_select'; ADMIN_TICKET_REPLY='admin_ticket_reply'; ADMIN_CUSTOMER_SELECT='admin_customer_select'; ADMIN_PHONE_SELECT='admin_phone_select'; ADMIN_FAQ_INPUT='admin_faq_input'; ADMIN_BROADCAST='admin_broadcast'
