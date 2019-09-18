from django_python3_ldap.utils import format_search_filters


def custom_format_search_filters(ldap_fields):
    # Call the base format callable.
    search_filters = format_search_filters(ldap_fields)
    # Advanced: apply custom LDAP filter logic.
    search_filters.append("(&(mail=*@globalraymac.ca))")

    return search_filters