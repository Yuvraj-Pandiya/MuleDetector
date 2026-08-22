"""
app/services/schema/canonical_schema.py
=========================================
Single Source of Truth for Canonical Internal AML Schema Definitions.

Defines:
  - Required fields: transaction_id, sender_account_id, receiver_account_id, amount, timestamp
  - Optional fields: transaction_type, balance, currency, device_id, ip_address, location,
                    old_balance_sender, new_balance_sender, old_balance_receiver, new_balance_receiver,
                    is_fraud, is_mule_pattern
  - Comprehensive Alias Dictionaries for enterprise multi-bank headers
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass
class CanonicalField:
    """Definition of a canonical field in the MuleDetector AML engine."""
    name: str
    required: bool
    expected_type: str  # 'string', 'float', 'datetime', 'integer', 'boolean'
    description: str
    aliases: Set[str] = field(default_factory=set)


# ---------------------------------------------------------------------------
# Required Canonical Fields
# ---------------------------------------------------------------------------

FIELD_TRANSACTION_ID = CanonicalField(
    name="transaction_id",
    required=True,
    expected_type="string",
    description="Unique transaction identifier.",
    aliases={
        "transaction_id", "txn_id", "transaction_no", "transaction_number",
        "reference_no", "reference_id", "ref_id", "tx_id", "txid", "payment_id",
        "id", "transfer_id", "uuid", "row_id", "txn_ref", "trans_id"
    },
)

FIELD_SENDER_ACCOUNT_ID = CanonicalField(
    name="sender_account_id",
    required=True,
    expected_type="string",
    description="Sender/Originator account identifier.",
    aliases={
        "sender", "sender_id", "sender_account", "sender_account_id",
        "from_account", "from_account_id", "source_account", "source_account_id",
        "debit_account", "debit_account_id", "origin_account", "originator_account",
        "nameorig", "orig_account", "from_acct", "source_acct", "payer", "payer_account",
        "remitter_account", "sending_account", "account_from"
    },
)

FIELD_RECEIVER_ACCOUNT_ID = CanonicalField(
    name="receiver_account_id",
    required=True,
    expected_type="string",
    description="Receiver/Beneficiary account identifier.",
    aliases={
        "receiver", "receiver_id", "receiver_account", "receiver_account_id",
        "to_account", "to_account_id", "destination_account", "destination_account_id",
        "credit_account", "credit_account_id", "beneficiary_account", "namedest",
        "dest_account", "to_acct", "dest_acct", "payee", "payee_account",
        "beneficiary", "receiving_account", "account_to"
    },
)

FIELD_AMOUNT = CanonicalField(
    name="amount",
    required=True,
    expected_type="float",
    description="Monetary value of the transaction.",
    aliases={
        "amount", "txn_amount", "transaction_amount", "transaction_value",
        "value", "transfer_amount", "debit_amount", "credit_amount",
        "amt", "txn_amt", "volume", "sum", "payment_amount", "val"
    },
)

FIELD_TIMESTAMP = CanonicalField(
    name="timestamp",
    required=True,
    expected_type="datetime",
    description="Transaction occurrence timestamp.",
    aliases={
        "timestamp", "datetime", "date_time", "transaction_time", "txn_time",
        "created_at", "event_time", "transaction_date", "date", "time",
        "step", "trans_date", "txn_datetime", "ts", "dt"
    },
)


# ---------------------------------------------------------------------------
# Optional Canonical Fields
# ---------------------------------------------------------------------------

FIELD_TRANSACTION_TYPE = CanonicalField(
    name="transaction_type",
    required=False,
    expected_type="string",
    description="Categorical transfer channel or mode (TRANSFER, CASH_OUT, PAYMENT).",
    aliases={
        "transaction_type", "txn_type", "type", "mode", "channel",
        "payment_mode", "payment_type", "transfer_type", "method"
    },
)

FIELD_IS_MULE_PATTERN = CanonicalField(
    name="is_mule_pattern",
    required=False,
    expected_type="integer",
    description="Supervised ground truth label (1=Mule/Fraud, 0=Legitimate).",
    aliases={
        "is_mule_pattern", "is_mule", "isfraud", "is_fraud", "fraud_label",
        "target", "label", "mule_label", "is_suspicious", "flag"
    },
)

FIELD_OLD_BALANCE_SENDER = CanonicalField(
    name="old_balance_sender",
    required=False,
    expected_type="float",
    description="Sender balance prior to transaction.",
    aliases={"oldbalanceorg", "old_balance_sender", "sender_old_balance", "orig_balance_before"},
)

FIELD_NEW_BALANCE_SENDER = CanonicalField(
    name="new_balance_sender",
    required=False,
    expected_type="float",
    description="Sender balance after transaction.",
    aliases={"newbalanceorig", "new_balance_sender", "sender_new_balance", "orig_balance_after"},
)

FIELD_OLD_BALANCE_RECEIVER = CanonicalField(
    name="old_balance_receiver",
    required=False,
    expected_type="float",
    description="Receiver balance prior to transaction.",
    aliases={"oldbalancedest", "old_balance_receiver", "receiver_old_balance", "dest_balance_before"},
)

FIELD_NEW_BALANCE_RECEIVER = CanonicalField(
    name="new_balance_receiver",
    required=False,
    expected_type="float",
    description="Receiver balance after transaction.",
    aliases={"newbalancedest", "new_balance_receiver", "receiver_new_balance", "dest_balance_after"},
)

FIELD_CURRENCY = CanonicalField(
    name="currency",
    required=False,
    expected_type="string",
    description="Currency code (USD, EUR, INR).",
    aliases={"currency", "curr", "ccy", "currency_code"},
)

FIELD_DEVICE_ID = CanonicalField(
    name="device_id",
    required=False,
    expected_type="string",
    description="Client device fingerprint ID.",
    aliases={"device_id", "device", "mac_address", "fingerprint"},
)

FIELD_IP_ADDRESS = CanonicalField(
    name="ip_address",
    required=False,
    expected_type="string",
    description="Client connection IP address.",
    aliases={"ip_address", "ip", "client_ip", "user_ip"},
)

FIELD_LOCATION = CanonicalField(
    name="location",
    required=False,
    expected_type="string",
    description="Transaction geographic location or country.",
    aliases={"location", "country", "city", "geo", "country_code"},
)


# Master Collections
CANONICAL_FIELDS: Dict[str, CanonicalField] = {
    "transaction_id": FIELD_TRANSACTION_ID,
    "sender_account_id": FIELD_SENDER_ACCOUNT_ID,
    "receiver_account_id": FIELD_RECEIVER_ACCOUNT_ID,
    "amount": FIELD_AMOUNT,
    "timestamp": FIELD_TIMESTAMP,
    "transaction_type": FIELD_TRANSACTION_TYPE,
    "is_mule_pattern": FIELD_IS_MULE_PATTERN,
    "old_balance_sender": FIELD_OLD_BALANCE_SENDER,
    "new_balance_sender": FIELD_NEW_BALANCE_SENDER,
    "old_balance_receiver": FIELD_OLD_BALANCE_RECEIVER,
    "new_balance_receiver": FIELD_NEW_BALANCE_RECEIVER,
    "currency": FIELD_CURRENCY,
    "device_id": FIELD_DEVICE_ID,
    "ip_address": FIELD_IP_ADDRESS,
    "location": FIELD_LOCATION,
}

REQUIRED_CANONICAL_FIELDS = {
    fname: field_obj for fname, field_obj in CANONICAL_FIELDS.items() if field_obj.required
}

# Source columns that MUST be present in raw CSV (transaction_id can be synthesized if missing)
MANDATORY_SOURCE_FIELDS = {
    "sender_account_id", "receiver_account_id", "amount", "timestamp"
}

OPTIONAL_CANONICAL_FIELDS = {
    fname: field_obj for fname, field_obj in CANONICAL_FIELDS.items() if not field_obj.required
}

# Reverse lookup alias dictionary mapping normalized alias -> canonical_field_name
ALIAS_DICTIONARY: Dict[str, str] = {}
for fname, field_obj in CANONICAL_FIELDS.items():
    ALIAS_DICTIONARY[fname] = fname
    for alias in field_obj.aliases:
        ALIAS_DICTIONARY[alias] = fname
