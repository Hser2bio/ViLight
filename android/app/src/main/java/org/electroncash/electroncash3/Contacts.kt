package org.electroncash.electroncash3

import android.arch.lifecycle.MutableLiveData
import android.arch.lifecycle.Observer
import android.content.Intent
import android.os.Bundle
import android.support.v4.app.Fragment
import android.support.v4.app.FragmentActivity
import android.support.v7.app.AlertDialog
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import com.chaquo.python.PyObject
import com.google.zxing.integration.android.IntentIntegrator
import kotlinx.android.synthetic.main.contact_detail.*
import kotlinx.android.synthetic.main.contacts.*


val libContacts by lazy { libMod("contacts") }

val contactsUpdate = MutableLiveData<Unit>().apply { value = Unit }


class ContactsFragment : Fragment(), MainFragment {
    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?,
                              savedInstanceState: Bundle?): View? {
        return inflater.inflate(R.layout.contacts, container, false)
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        setupVerticalList(rvContacts)
        rvContacts.adapter = ContactsAdapter(activity!!)

        daemonUpdate.observe(viewLifecycleOwner, Observer { refresh() })
        contactsUpdate.observe(viewLifecycleOwner, Observer { refresh() })
        settings.getBoolean("cashaddr_format").observe(viewLifecycleOwner, Observer {
            rvContacts.adapter?.notifyDataSetChanged()
        })

        btnAdd.setOnClickListener { showDialog(activity!!, ContactDialog()) }
    }

    fun refresh() {
        val wallet = daemonModel.wallet
        (rvContacts.adapter as ContactsAdapter).submitList(
            if (wallet == null) null else listContacts())
    }
}


class ContactsAdapter(val activity: FragmentActivity)
    : BoundAdapter<ContactModel>(R.layout.contact_list) {

    override fun onBindViewHolder(holder: BoundViewHolder<ContactModel>, position: Int) {
        super.onBindViewHolder(holder, position)
        holder.itemView.setOnClickListener {
            showDialog(activity, ContactDialog().apply {
                arguments = holder.item.toBundle()
            })
        }
    }
}


class ContactModel(val name: String, val addr: PyObject) {
    constructor(args: Bundle) : this(args.getString("name")!!,
                                     makeAddress(args.getString("address")!!))
    val addrUiString
        get() = addr.callAttr("to_ui_string").toString()
    val addrStorageString
        get() = addr.callAttr("to_storage_string").toString()

    fun toBundle(): Bundle {
        return Bundle().apply {
            putString("name", name)
            putString("address", addrStorageString)
        }
    }
}


class ContactDialog : AlertDialogFragment() {
    val existingContact by lazy {
        if (arguments == null) null
        else ContactModel(arguments!!)
    }

    override fun onBuildDialog(builder: AlertDialog.Builder) {
        with (builder) {
            setView(R.layout.contact_detail)
            setNegativeButton(android.R.string.cancel, null)
            setPositiveButton(android.R.string.ok, null)
            setNeutralButton(if (existingContact == null) R.string.qr_code
                             else R.string.delete,
                             null)
        }
    }

    override fun onShowDialog(dialog: AlertDialog) {
        dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener { onOK() }

        val contact = existingContact
        if (contact == null) {
            for (btn in listOf(dialog.btnExplore, dialog.btnSend)) {
                (btn as View).visibility = View.INVISIBLE
            }
            dialog.getButton(AlertDialog.BUTTON_NEUTRAL).setOnClickListener { scanQR(this) }
        } else {
            dialog.btnExplore.setOnClickListener {
                exploreAddress(activity!!, contact.addr)
            }
            dialog.btnSend.setOnClickListener {
                try {
                    showDialog(activity!!, SendDialog().apply {
                        arguments = Bundle().apply {
                            putString("address", contact.addrUiString)
                        }
                    })
                    dismiss()
                } catch (e: ToastException) { e.show() }
            }
            dialog.getButton(AlertDialog.BUTTON_NEUTRAL).setOnClickListener {
                showDialog(activity!!, DeleteContactDialog().apply {
                    arguments = contact.toBundle()
                })
            }
        }
    }

    override fun onFirstShowDialog(dialog: AlertDialog) {
        val contact = existingContact
        if (contact != null) {
            dialog.etName.setText(contact.name)
            dialog.etAddress.setText(contact.addrUiString)
        }
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        val result = IntentIntegrator.parseActivityResult(requestCode, resultCode, data)
        if (result != null && result.contents != null) {
            dialog.etAddress.setText(result.contents)
        } else {
            super.onActivityResult(requestCode, resultCode, data)
        }
    }

    fun onOK() {
        val name = dialog.etName.text.toString()
        val address = dialog.etAddress.text.toString()
        try {
            if (name.isEmpty()) {
                throw ToastException(R.string.name_is, Toast.LENGTH_SHORT)
            }
            val newContact = makeContact(name, makeAddress(address))
            val oldContact =
                if (existingContact == null) null
                else makeContact(existingContact!!.name, existingContact!!.addr)
            val wallet = daemonModel.wallet!!
            wallet.get("contacts")!!.callAttr("add", newContact, oldContact)
            wallet.get("storage")!!.callAttr("write")
            contactsUpdate.setValue(Unit)
            dismiss()
        } catch (e: ToastException) { e.show() }
    }
}


class DeleteContactDialog : AlertDialogFragment() {
    override fun onBuildDialog(builder: AlertDialog.Builder) {
        val contact = ContactModel(arguments!!)
        builder.setTitle(R.string.confirm_delete)
            .setMessage(R.string.are_you_sure_you_wish_to_delete)
            .setPositiveButton(R.string.delete) { _, _ ->
                val wallet = daemonModel.wallet!!
                wallet.get("contacts")!!.callAttr(
                    "remove", makeContact(contact.name, contact.addr))
                wallet.get("storage")!!.callAttr("write")
                contactsUpdate.setValue(Unit)
                findDialog(activity!!, ContactDialog::class)!!.dismiss()
            }
            .setNegativeButton(android.R.string.cancel, null)
    }
}


fun listContacts(): List<ContactModel> {
    val contacts = ArrayList<ContactModel>()
    for (contact in daemonModel.wallet!!.get("contacts")!!.callAttr("get_all").asList()) {
        contacts.add(ContactModel(contact.get("name").toString(),
                                  makeAddress(contact.get("address").toString())))
    }
    contacts.sortBy { it.name }
    return contacts
}


fun makeContact(name: String, addr: PyObject): PyObject {
    return libContacts.callAttr(
        "Contact", name, addr.callAttr("to_storage_string"), "address")!!
}