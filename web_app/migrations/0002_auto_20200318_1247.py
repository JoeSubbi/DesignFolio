# Generated by Django 2.2.3 on 2020-03-18 12:47

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('web_app', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='posts',
            name='tags',
        ),
        migrations.CreateModel(
            name='PostTags',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pid', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='web_app.Posts')),
                ('tag', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='web_app.Tags')),
            ],
        ),
    ]
