import csv
from django.http import HttpResponse

def export_as_csv(modeladmin, request, queryset):
    """
    Generic admin action to export selected queryset to CSV.
    """
    meta = modeladmin.model._meta
    field_names = [field.name for field in meta.fields]

    response = HttpResponse(content_type='text/csv')
    filename = f'{meta.verbose_name_plural.lower().replace(" ", "_")}_export.csv'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(field_names)

    for obj in queryset:
        row = []
        for field in field_names:
            val = getattr(obj, field)
            if callable(val):
                val = val()
            row.append(str(val))
        writer.writerow(row)

    return response

export_as_csv.short_description = "📥 Export Selected to CSV"
