import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'xBrain.settings')
django.setup()

from api.models import Specialization


def seed_specializations():
    specializations_data = [
        {
            "name": "Back-end development",
            "description": "Server-side development, RESTful APIs, databases, and business logic implementation"
        },
        {
            "name": "Front-end development",
            "description": "User interfaces, responsive design, web applications using HTML, CSS, JavaScript, and modern frameworks"
        },
        {
            "name": "Mobile development",
            "description": "Native and cross-platform mobile applications for iOS and Android using React Native, Flutter, or native technologies"
        },
        {
            "name": "Data science",
            "description": "Data analysis, statistical modeling, data visualization, and extracting insights from large datasets"
        },
        {
            "name": "Machine learning",
            "description": "ML algorithms, model training, feature engineering, and deploying predictive models"
        },
        {
            "name": "Artificial intelligence",
            "description": "AI systems, natural language processing, computer vision, and deep learning applications"
        },
        {
            "name": "Cybersecurity",
            "description": "Network security, ethical hacking, penetration testing, and protecting systems from threats"
        },
        {
            "name": "Cloud computing",
            "description": "AWS, Azure, Google Cloud Platform, cloud architecture, and cloud-native applications"
        },
        {
            "name": "DevOps",
            "description": "CI/CD pipelines, Docker, Kubernetes, infrastructure as code, and automation"
        },
        {
            "name": "Databases",
            "description": "SQL and NoSQL databases, database design, optimization, and data modeling"
        },
    ]
    
    print("Seeding specializations...\n")
    
    created_count = 0
    existing_count = 0
    
    for spec_data in specializations_data:
        spec, created = Specialization.objects.get_or_create(
            name=spec_data["name"],
            defaults={"description": spec_data["description"]}
        )
        
        if created:
            print(f"Created: {spec.name}")
            created_count += 1
        else:
            print(f"Already exists: {spec.name}")
            existing_count += 1
    
    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"Created: {created_count} specializations")
    print(f"Already existed: {existing_count} specializations")
    print(f"Total in database: {Specialization.objects.count()} specializations")
    print(f"{'='*60}\n")
    print("Specializations seeding complete!")


if __name__ == "__main__":
    seed_specializations()
