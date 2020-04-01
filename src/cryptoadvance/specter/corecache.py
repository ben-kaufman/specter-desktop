
cache = {}

class CoreCache():
    def __init__(self, wallet, walletname, cli):
        self.cli = cli
        self.wallet = wallet
        self.walletname = walletname
        self.setup_cache()


    def setup_cache(self):
        """Setup cache if don't exist yet for the wallet
        """
        if self.walletname in cache:
            if "cli_txs" not in cache[self.walletname]:
                cache[self.walletname]["cli_txs"] = {}
            if "raw_transactions" not in cache[self.walletname]:
                cache[self.walletname]["raw_transactions"] = {}
            if "transactions" not in cache[self.walletname]:
                cache[self.walletname]["transactions"] = []
            if "addresses" not in cache[self.walletname]:
                cache[self.walletname]["addresses"] = []
            if "tx_count" not in cache[self.walletname]:
                cache[self.walletname]["tx_count"] = None
            if "tx_changed" not in cache[self.walletname]:
                cache[self.walletname]["tx_changed"] = True
            if "labels" not in cache[self.walletname]:
                cache[self.walletname]["labels"] = {}
            if "last_block" not in cache[self.walletname]:
                cache[self.walletname]["last_block"] = None
        else:
            cache[self.walletname] = {
                "cli_txs": {},
                "raw_transactions": {},
                "transactions": [],
                "addresses": [],
                "tx_count": None,
                "tx_changed": True,
                "labels": {},
                "last_block": None
            }

    def cache_cli_txs(self):
        ''' Cache Bitcoin Core `listtransactions` result
            manages ["cli_txs"]
        '''
        cache[self.walletname]["cli_txs"] = {tx["txid"]: tx for tx in self.transactions}
        return cache[self.walletname]["cli_txs"]

    def cache_addresses(self):
        ''' Cache wallet addresses
            manages ["active_addresses"] and ["addresses"]
        '''
        # addresses: 
        # addresses = [self.get_address(idx) for idx in range(0,self._dict["address_index"] + 1)]
        # return list(dict.fromkeys(addresses + self.utxoaddresses))
        cache[self.walletname]["active_addresses"] = list(dict.fromkeys(self.wallet.addresses))
        cache[self.walletname]["addresses"] = list(dict.fromkeys(self.wallet.addresses + self.wallet.change_addresses))

    def cache_raw_txs(self):
        """ Cache `raw_transactions` (with full data on all the inputs and outputs of each tx)
            This is safe to call more often and it updates automatically
        """
        # Get list of all tx ids
        txids = list(dict.fromkeys(cache[self.walletname]["cli_txs"].keys()))
        tx_count = len(txids)
        # If there are new transactions (if the transations count changed)
        if tx_count != cache[self.walletname]["tx_count"]:
            for txid in txids:
                # Cache each tx, if not already cached.
                # Data is immutable (unless reorg occurs and except of confirmations) and can be saved in a file for permanent caching
                if txid not in cache[self.walletname]["raw_transactions"]:
                    # Call Bitcoin Core to get the "raw" transaction - allows to read detailed inputs and outputs
                    raw_tx_hex = self.cli.gettransaction(txid)["hex"]
                    raw_tx = self.cli.decoderawtransaction(raw_tx_hex)
                    # Some data (like fee and category, and when unconfirmed also time) available from the `listtransactions`
                    # command is not available in the `getrawtransacion` - so add it "manually" here.
                    if "fee" in cache[self.walletname]["cli_txs"][txid]:
                        raw_tx["fee"] = cache[self.walletname]["cli_txs"][txid]["fee"]
                    if "category" in cache[self.walletname]["cli_txs"][txid]:
                        raw_tx["category"] = cache[self.walletname]["cli_txs"][txid]["category"]
                    if "time" in cache[self.walletname]["cli_txs"][txid]:
                        raw_tx["time"] = cache[self.walletname]["cli_txs"][txid]["time"]

                    # Loop on the transaction's inputs
                    # If not a coinbase transaction:
                    # Get the the output data corresponding to the input (that is: input_txid[output_index])
                    tx_ins = []
                    for vin in raw_tx["vin"]:
                        # If the tx is a coinbase tx - set `coinbase` to True
                        if "coinbase" in vin:
                            raw_tx["coinbase"] = True
                            break
                        # If the tx is a coinbase tx - set `coinbase` to True
                        vin_txid = vin["txid"]
                        vin_vout = vin["vout"]
                        try:
                            raw_tx_hex = self.cli.gettransaction(vin_txid)["hex"]
                            tx_in = self.cli.decoderawtransaction(raw_tx_hex)["vout"][vin_vout]
                            tx_in["txid"] = vin["txid"]
                            tx_ins.append(tx_in)
                        except:
                            pass
                    # For each output in the tx_ins list (the tx inputs in their output "format")
                    # Create object with the address, amount, and whatever the address belongs to the wallet (`internal=True` if it is).
                    raw_tx["from"] = [{"address": out["scriptPubKey"]["addresses"][0], "amount": out["value"], "internal": out["scriptPubKey"]["addresses"][0] in cache[self.walletname]["addresses"]} for out in tx_ins]
                    # For each output in the tx (`vout`)
                    # Create object with the address, amount, and whatever the address belongs to the wallet (`internal=True` if it is).
                    raw_tx["to"] = [({"address": out["scriptPubKey"]["addresses"][0], "amount": out["value"], "internal": out["scriptPubKey"]["addresses"][0] in cache[self.walletname]["addresses"]}) for out in raw_tx["vout"] if "addresses" in out["scriptPubKey"]]
                    # Save the raw_transaction to the cache
                    cache[self.walletname]["raw_transactions"][txid] = raw_tx
            # Set the tx count to avoid unnecessary indexing
            cache[self.walletname]["tx_count"] = tx_count
            # Set the tx changed to indicate the there are new transactions to cache
            cache[self.walletname]["tx_changed"] = True
        else:
            # Set the tx changed to False to avoid unnecessary indexing
            cache[self.walletname]["tx_changed"] = False
        return cache[self.walletname]["raw_transactions"]

    def cache_labels(self):
        """ Cache labels for addresses (if not cached already)
            This method won't self-update the cache.
            This needs to be done via the update_cache_label-method
            The getlabel-method won't check for an existing label if cache is empty for that address
        """
        if len(cache[self.walletname]["labels"]) == 0:
            cache[self.walletname]["labels"] = {address: self.getlabel(address) for address in cache[self.walletname]["addresses"]}
        return cache[self.walletname]["labels"]
    
    def update_cache_label(self, addr, label):
        ''' updates the label of that addr in the cache
            this method needs to be called because no other update mechanism
            will ensure the consistency of the cache (other then the other parts of the cache)
        '''
        old_label = cache[self.walletname]["labels"][addr] if addr in cache[self.walletname]["labels"] else addr
        cache[self.walletname]["labels"][addr] = label
        for i, tx in enumerate(self.transactions):
            if tx["label"] == old_label if "label" in tx else tx["address"] == old_label:
                self.transactions[i]["label"] = label
    
    def getlabel(self, addr):
        if addr in cache[self.walletname]["labels"]:
            return cache[self.walletname]["labels"][addr]
        # We could query now but that would be quite inefficient for a cache
        # where most addresses might not have a label
        # This cache is in danger of getting outdated if not used properly!
        return None
    
    def cache_confirmations(self):
        """Update the confirmations count for txs.
        """
        # Get the block count from Bitcoin Core
        blocks = self.cli.getblockcount()
        # If there are new blocks since the last cache update
        if blocks != cache[self.walletname]["last_block"] or cache[self.walletname]["tx_changed"]:
            # Loop through the cached `transactions` and update its confirmations according to the cached `cli_txs` data 
            for i in range(0, len(cache[self.walletname]["transactions"])):
                confs = cache[self.walletname]["cli_txs"][cache[self.walletname]["transactions"][i]["txid"]]["confirmations"]
                cache[self.walletname]["transactions"][i]["confirmations"] = confs

            # Update last block confirmations were cached for
            cache[self.walletname]["last_block"] = blocks

    def cache_txs(self):
        """Caches the transactions list.
            Cache the inputs and outputs which belong to the user's wallet for each `raw_transaction` 
            This method relies on a few assumptions regarding the txs format to cache data properly:
                - In `send` transactions, all inputs belong to the wallet.
                - In `send` transactions, there is only one output not belonging to the wallet (i.e. only one recipient).
                - In `coinbase` transactions, there is only one input.
                - Change addresses are derived from the path used by Specter
        """
        # Get the cached `raw_transactions` dict (txid -> tx) as a list of txs
        transactions = list(sorted(cache[self.walletname]["raw_transactions"].values(), key = lambda tx: tx['time'], reverse=True))
        result = []

        # If the `raw_transactions` did not change - exit here.
        #if not cache[self.walletname]["tx_changed"]:
        #    return

        # Loop through the raw_transactions list
        for i, tx in enumerate(transactions):
            # If tx is a user generated one (categories: `send`/ `receive`) and not coinbase (categories: `generated`/ `immature`)
            if tx["category"] == "send" or tx["category"] == "receive":
                is_send = True
                is_self = True

                # Check if the transaction is a `send` or not (if all inputs belong to the wallet)
                if len(tx["from"]) == 0:
                    is_send = False

                for fromdata in tx["from"]:
                    if not fromdata["internal"]:
                        is_send = False

                # Check if the transaction is a `self-transfer` (if all inputs and all outputs belong to the wallet)
                for to in tx["to"]:
                    if not is_send or not to["internal"]:
                        is_self = False
                        break

                tx["is_self"] = is_self

                if not is_send or is_self:
                    for to in tx["to"]:
                        if to["internal"]:
                            # Cache received outputs
                            result.append(self.wallet.prepare_tx(tx, to, "receive", destination=None, is_change=(to["address"] in self.wallet.change_addresses)))

                if is_send or is_self:
                    destination = None
                    for to in tx["to"]:
                        if to["address"] in self.wallet.change_addresses:
                            # Cache change output
                            result.append(self.wallet.prepare_tx(tx, to, "receive", destination=destination, is_change=True))
                        elif not to["internal"] or (is_self and to["address"] not in self.wallet.change_addresses):
                            destination = to
                    for fromdata in tx["from"]:
                        # Cache sent inputs
                        result.append(self.wallet.prepare_tx(tx, fromdata, "send", destination=destination))
            else:
                tx["is_self"] = False
                # Cache coinbase output
                result.append(self.wallet.prepare_tx(tx, tx["to"][0], tx["category"]))

        # Save the result to the cache
        cache[self.walletname]["transactions"] = result
        return cache[self.walletname]["transactions"]

    def update_cache(self):
        self.setup_cache()
        self.cache_cli_txs()
        self.cache_addresses()
        self.cache_labels()
        self.cache_raw_txs()
        self.cache_txs()
        self.cache_confirmations()

    def rebuild_cache(self):
        del cache[self.walletname]
        self.update_cache()

    @property
    def transactions(self):
        ''' non cached results '''
        #if self.walletname not in cache or "transactions" not in cache[self.walletname] or len(cache[self.walletname]["transactions"]) == 0:
            # ToDo: why not updating the cache and then return the cache-result?
        return self.cli.listtransactions("*", 1000, 0, True)[::-1]
        #return cache[self.walletname]["transactions"]


    @property
    def utxo():
        if self._utxo == None:
            try:
                self._utxo = self.cli.listunspent(0)
            except:
                self._utxo = None
        return self._utxo
        
    @property
    def utxoaddresses(self):
        return list(dict.fromkeys([
            utxo["address"] for utxo in 
            sorted(
                self.utxo,
                key = lambda utxo: self.cache[self.walletname]["cli_txs"][utxo["txid"]]["time"]
            )
        ]))
