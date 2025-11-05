from datetime import datetime
from typing import Optional

from idp.framework.examples.domain.entity.stop import Stop
from idp.framework.examples.domain.vo.contact import Contact
from idp.framework.examples.domain.vo.location import Location
from idp.framework.examples.infrastructure.persistence.po.stop import StopPO
from idp.framework.infrastructure.mapper.core.mapper import MapperBuilder


def create_stop_mapper():
    def po_to_location(po):
        if po.latitude is not None and po.longitude is not None:
            return Location(latitude=po.latitude, longitude=po.longitude)
        return None

    def po_to_contact(po):
        if po.contact_name or po.contact_phone or po.contact_email:
            return Contact(
                name=po.contact_name,
                phone=po.contact_phone,
                email=po.contact_email
            )
        return None

    return (
        MapperBuilder.for_types(Stop, StopPO)
        .map('id', 'id')
        .map('tenant_id', 'tenant_id')
        .map('name', 'name')
        .map('description', 'description')
        .map('address', 'address')
        .map('is_active', 'is_active')
        .map_custom('created_at', lambda s: datetime.utcnow())
        .map_custom('updated_at', lambda s: datetime.utcnow())
        .map_custom('created_by', lambda s: '')
        .map_custom('updated_by', lambda s: '')
        .map_custom('deleted_at', lambda s: None)
        .map_custom('deleted_by', lambda s: '')
        .map_custom('latitude', lambda s: s.location.latitude if s.location else None)
        .map_custom('longitude', lambda s: s.location.longitude if s.location else None)
        .map_custom('contact_name', lambda s: s.contact.name if s.contact else None)
        .map_custom('contact_phone', lambda s: s.contact.phone if s.contact else None)
        .map_custom('contact_email', lambda s: s.contact.email if s.contact else None)
        .map_reverse('location', po_to_location)
        .map_reverse('contact', po_to_contact)
        .build()
    )
