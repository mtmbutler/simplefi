from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from budget.models import Budget, TransactionClass


class Command(BaseCommand):
    help = "Ensures TransactionClass objects are created."

    def handle(self, *args, **options):
        for c in TransactionClass.CLASSES:
            # Make sure each option exists
            tc, new = TransactionClass.objects.get_or_create(name=c[0])
            if new:
                tc.save()

            # Make sure each user has a budget for each class
            User = get_user_model()
            for u in User.objects.all():
                b, new = Budget.objects.get_or_create(
                    user=u, class_field=tc, defaults={"value": 0.0}
                )
                if new:
                    b.save()

        self.stdout.write(self.style.SUCCESS("Done!"))
