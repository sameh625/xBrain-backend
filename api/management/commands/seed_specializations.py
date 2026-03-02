from django.core.management.base import BaseCommand
from api.models import Specialization

class Command(BaseCommand):
    help = 'Seeds the database with initial specializations'

    def handle(self, *args, **kwargs):
        specializations = [
            {
                "name": "Frontend Development",
                "description": "Building client-side applications using HTML, CSS, JavaScript, and frameworks like React, Vue, or Angular."
            },
            {
                "name": "Backend Development",
                "description": "Building server-side logic, databases, APIs, and architecture using languages like Python, Node.js, Java, or Go."
            },
            {
                "name": "Full Stack Development",
                "description": "Working on both frontend and backend development to create complete web applications."
            },
            {
                "name": "Mobile Development",
                "description": "Building applications for mobile devices (iOS/Android) using Swift, Kotlin, Flutter, or React Native."
            },
            {
                "name": "Data Science",
                "description": "Analyzing complex data, building machine learning models, and extracting insights using Python, R, and SQL."
            },
            {
                "name": "DevOps Engineering",
                "description": "Managing cloud infrastructure, CI/CD pipelines, and application deployment using Docker, Kubernetes, and AWS."
            },
            {
                "name": "UI/UX Design",
                "description": "Designing user interfaces and experiences, focusing on usability, accessibility, and visual aesthetics."
            },
            {
                "name": "Cybersecurity",
                "description": "Protecting systems, networks, and programs from digital attacks, and ensuring data privacy."
            }
        ]

        count = 0
        for spec_data in specializations:
            obj, created = Specialization.objects.get_or_create(
                name=spec_data["name"],
                defaults={"description": spec_data["description"]}
            )
            if created:
                count += 1
                self.stdout.write(self.style.SUCCESS(f'Created specialization: {obj.name}'))

        self.stdout.write(self.style.SUCCESS(f'Successfully seeded {count} new specializations. Total: {Specialization.objects.count()}'))
