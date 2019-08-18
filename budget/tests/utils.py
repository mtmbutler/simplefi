def login(client, django_user_model):
    params = dict(username="test", password="testpw")
    user = django_user_model.objects.create_user(**params)
    client.login(**params)

    return user
