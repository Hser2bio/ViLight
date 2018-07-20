from .transaction import Transaction
from enum import Enum

# This class has sole responsibility for creating NEW SLP token transactions
class SlpTokenTransactionFactory():
    def __init__(token_version: SlpTokenVersion = SlpTokenVersion.TYPE_0001,
                    token_id: bytearray = None):
        self.token_version = token_version
        self.token_id = token_id
        self.lokad_id: str = '00534c50'

    def buildInitTransaction(self, inputs, output_mint_reciever, output_baton_reciever, ascii_ticker: str, token_name: str, token_document_ascii_url: str,  token_document_hash: bytearray, initial_token_mint_quantity: int, max_final_token_supply: int = None) -> SlpTransaction:
        tx = SlpTransaction(SlpTransactionType.INIT, self.token_version, None)
        tx.add_inputs(inputs)
        vouts = []
        vouts.append(self.buildInitOpReturnOutput(ascii_ticker, token_name, token_document_ascii_url, token_document_hash, initial_token_mint_quantity, max_final_token_supply))
        vouts.append(output_mint_reciever)
        if output_baton_reciever is not None:
            vouts.append(output_baton_reciever)
        return tx

    def buildTransferTransaction(self, inputs, outputs, comment: str, output_token_quantity_array: []int) -> SlpTransaction:
        if self.token_id == None:
            raise SlpTokenIdMissing
        tx = SlpTransaction(SlpTransactionType.TRAN, self.token_version, self.token_id)
        tx.add_inputs(inputs)
        vouts = []
        vouts.append(self.buildTransferOpReturnOutput(comment, output_token_quantity_array))
        vouts.extend(outputs)
        return tx

    # def buildMintTransaction(self, mint_quantity: int) -> SlpTransaction:
    #     if self.token_id == None:
    #         raise SlpTokenIdMissing
    #     raise Exception("Not Implemented.")

    # def buildIssuerCommitmentTransaction(self, for_bitcoin_block_height: int, for_bitcoin_block_hash: bytearray, 
    #                                             token_txn_set_commitment: bytearray, txn_set_data_url: str) -> Transaction:
    #     if self.token_id == None:
    #         raise SlpTokenIdMissing
    #     raise Exception("Not Implemented.")

    def buildInitOpReturnOutput(self, ascii_ticker: str, token_name: str, 
                                token_document_ascii_url: str, token_document_hash: bytearray, 
                                initial_token_mint_quantity: int, max_final_token_supply: int = None) -> Transaction:
        script = "OP_RETURN " + \
                    self.lokad_id + " " + \
                    self.token_version + \
                    " INIT " + \
                    ascii_ticker + " " + \
                    token_name + " " + \
                    token_document_ascii_url + " " + \
                    token_document_hash + " " + \
                    initial_token_mint_quantity

        # TODO: handle max_final_token_supply --- future baton case
        scriptBuffer = ScriptOutput.from_string(script)
        if len(scriptBuffer.script) > 223:
            raise OPReturnTooLarge(_("OP_RETURN message too large, needs to be under 220 bytes"))
        return (TYPE_SCRIPT, scriptBuffer, 0)

    def buildTransferOpReturnOutput(self, comment, output_qty_array):
        script = "OP_RETURN " + \
                    self.lokad_id + " " + \
                    self.token_version + \
                    " TRAN " + \
                     self.token_id

        if len(output_qty_array) > 20: 
            raise Exception("Cannot have more than 20 SLP Token outputs.")
        for qty in output_qty_array:
            script = script + " " + self.token_id + " " + qty
        scriptBuffer = ScriptOutput.from_string(script)
        if len(scriptBuffer.script) > 223:
            raise OPReturnTooLarge(_("OP_RETURN message too large, needs to be under 220 bytes"))
        return (TYPE_SCRIPT, scriptBuffer, 0)

    # def buildMintOpReturnOutput(self, additional_token_quantity):
    #     script = "OP_RETURN " + self.lokad_id + " " + self.token_version + " MINT"
    #     script = script + " " + self.token_id + " " + additional_token_quantity
    #     scriptBuffer = ScriptOutput.from_string(script)
    #     if len(scriptBuffer.script) > 223:
    #         raise OPReturnTooLarge(_("OP_RETURN message too large, needs to be under 220 bytes"))
    #     return (TYPE_SCRIPT, scriptBuffer, 0)

    # def buildCommitmentOpReturnOutput(self, for_bitcoin_block_height, for_bitcoin_block_hash, token_txn_set_commitment, txn_set_data_url):
    #     script = "OP_RETURN " + self.lokad_id + " " + self.token_version + " COMM"
    #     script = script + " " + self.token_id + " " + for_bitcoin_block_height + " " + for_bitcoin_block_height
    #     script = script + " " + token_txn_set_commitment + " " + txn_set_data_url
    #     scriptBuffer = ScriptOutput.from_string(script)
    #     if len(scriptBuffer.script) > 223:
    #         raise OPReturnTooLarge(_("OP_RETURN message too large, needs to be under 220 bytes"))
    #     return (TYPE_SCRIPT, scriptBuffer, 0)

class SlpTransaction(Transaction):
    def __init__(self, raw, transaction_type: SlpTrasnsactionType, token_type: SlpTokenVersion, token_id: bytes):
        super.__init__(raw)

        self.isChecked = False
        self.isSlpToken = False
        self.isSupportedTokenVersion = False
        self.lokad_id: str = '00534c50'
        self.token_version = token_type
        self.token_id = token_id
        self.transaction_type: SlpTransactionType = transaction_type

    @staticmethod
    def parseSlpOutputScript(outputScript: ScriptOutput) -> SlpTransaction:

        # convert raw script to ASM Human-readable format w/o pushdata commands
        asm = outputScript.to_asm()

        # Split asm format with spaces
        split_asm = asm.split(' ')

        # check script is OP_RETURN
        if split_asm[0] is not 'OP_RETURN':
            raise SlpInvalidOutputMessage()

        # check that the locad ID is correct
        if split_asm[1] is not self.lokad_id:
            raise SlpInvalidOutputMessage()

        # check if the token version is supported
        if len(split_asm[2]) is not 4:
            raise SlpInvalidOutputMessage()

        # check if the slp transaction type is valid
        if not (split_asm[3].decode('ascii') is SlpTransactionType.INIT or split_asm[3].decode('ascii') is SlpTransactionType.TRAN):
            raise SlpInvalidOutputMessage()

        self.isSlpToken

        if split_asm[2] is SlpTokenVersion.TYPE_0001:
            self.isSupportedTokenVersion = True
        else:
            raise SlpUnsupportedSlpTokenType()

        # switch statement to handle different on transaction type
        if split_asm[3].decode('ascii') is SlpTransactionType.INIT:

            # TEMPLATE FROM ABOVE:
                # "OP_RETURN " + \
                # self.lokad_id + " " + \
                # self.token_version + \
                # " INIT " + \
                # ascii_ticker + " " + \
                # token_name + " " + \
                # token_document_ascii_url + " " + \
                # token_document_hash + " " + \
                # initial_token_mint_quantity

            # handle ascii ticker
            try:
                ticker = split_asm[4].decode('ascii')
            except:
                raise SlpInproperlyFormattedTransaction()

            # handle token name
            try:
                token_name = split_asm[5].decode('utf-8')
            except UnicodeDecodeError:
                raise SlpInproperlyFormattedTransaction()

            # handle token docuemnt url
            try:
                token_doc_url = split_asm[6].decode('utf-8')
            except UnicodeDecodeError:
                raise SlpInproperlyFormattedTransaction() 

            # handle token docuemnt hash
            try:
                token_doc_hash = binascii.bh2b(split_asm[7])
            except ???:
                raise SlpInproperlyFormattedTransaction() 

            # handle initial token quantity issuance
            try:
                token_quantity = int(split_asm[8])
            except UnicodeDecodeError:
                raise SlpInproperlyFormattedTransaction() 

        elif split_asm[3].decode('ascii') is SlpTransactionType.TRAN:

            # "OP_RETURN " + \
            # self.lokad_id + " " + \
            # self.token_version + \
            # " TRAN " + \
            # self.token_id
            # <QUANTITIES HERE>

            try:

            


    @staticmethod
    def isSlpTransferOutputMessage(output):
        pass

class SlpTokenVersion(Enum):
    TYPE_0001 = '0001'

class SlpTransactionType(Enum):
    INIT = "INIT"
    #MINT = "MINT"
    TRAN = "TRAN"
    #COMM = "COMM"

class SlpInvalidOutputMessage(Exception):
    pass

class SlpUnsupportedSlpTokenType(Exception):
    pass

class SlpTokenIdMissing(Exception):
    pass