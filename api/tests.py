from unittest.mock import patch

from django.core import mail
from django.urls import reverse
from django.utils import timezone
from django.test.utils import override_settings

from django.http import HttpRequest

from api.models import AccessDevice
from drfx import settings
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase
from rest_framework_tracking.models import APIRequestLog
from users.models import CustomUser, MemberService, NFCCard, ServiceSubscription
from api.mulysaoauthvalidator import MulysaOAuth2Validator


class TestOAuthValidator(APITestCase):
    def setUp(self):
        # and test user
        self.ok_user = CustomUser.objects.create(
            email="test1@example.com",
            birthday=timezone.now(),
            phone="+35844055066",
            mxid="@ok:exmaple.com",
        )
        self.ok_user.save()

    def test_oauthvalidator(self):
        req = HttpRequest()
        req.user = self.ok_user
        expected = {
            "sub": self.ok_user.email,
            "email": self.ok_user.email,
            "firstName": self.ok_user.first_name,
            "lastName": self.ok_user.last_name,
        }
        oauthvalidator = MulysaOAuth2Validator()
        res = oauthvalidator.get_additional_claims(req)
        self.assertDictEqual(expected, res)

    def tearDown(self):
        CustomUser.objects.all().delete()


@patch("api.views.VerySlowThrottle.allow_request", return_value=True)
class TestLogging(APITestCase):
    fixtures = ["users/fixtures/memberservices.json"]

    def setUp(self):
        # create test device
        self.device = AccessDevice.objects.create(
            deviceid="testdevice",
        )
        # and test user
        self.ok_user = CustomUser.objects.create(
            email="test1@example.com",
            birthday=timezone.now(),
            phone="+35844055066",
            mxid="@ok:exmaple.com",
        )
        self.ok_user.save()

    def test_access_phone_list_unauthenticated(self, mock):
        url = reverse("access-phone")
        data = {"deviceid": self.device.deviceid, "payload": self.ok_user.phone}
        response = self.client.post(url, data)
        # someone wanted these strange status_codes :)
        self.assertEqual(response.status_code, 481)
        # check that we have a drf-tracking log entry
        self.assertEqual(APIRequestLog.objects.count(), 1)
        self.assertIn(self.ok_user.phone, APIRequestLog.objects.first().data)
        self.assertIn(self.ok_user.email, APIRequestLog.objects.first().response)

    def tearDown(self):
        CustomUser.objects.all().delete()
        Token.objects.all().delete()


@patch("api.views.VerySlowThrottle.allow_request", return_value=True)
class TestAccess(APITestCase):
    fixtures = ["users/fixtures/memberservices.json"]

    def setUp(self):
        # create test superuser for authenticated calls
        self.superuser = CustomUser.objects.create_superuser(
            "admin@example.com", "FirstName", "LastName", "+358123", "hunter2"
        )
        self.superuser_token = Token.objects.create(user=self.superuser)

        # create test device
        self.device = AccessDevice.objects.create(
            deviceid="testdevice",
        )

        # and test user
        self.ok_user = CustomUser.objects.create(
            email="test1@example.com",
            birthday=timezone.now(),
            phone="+35844055066",
            mxid="@ok:exmaple.com",
        )
        self.ok_user.save()

        # add subscription for the user
        self.ok_subscription = ServiceSubscription.objects.create(
            user=self.ok_user,
            service=MemberService.objects.get(pk=settings.DEFAULT_ACCOUNT_SERVICE),
            state=ServiceSubscription.ACTIVE,
        )
        self.ok_subscription.save()

        # and test card
        self.ok_card = NFCCard.objects.create(
            user=self.ok_user,
            cardid="ABC123TEST",
        )
        self.ok_card.save()
        # and another test card for the same user
        self.ok_card2 = NFCCard.objects.create(
            user=self.ok_user,
            cardid="ABC123TEST2",
        )
        self.ok_card2.save()

        # user with no access
        self.fail_user = CustomUser.objects.create(
            email="test2@example.com",
            birthday=timezone.now(),
            phone="+35855044033",
            mxid="@fail:exmaple.com",
        )
        # with suspended service
        self.fail_subscription = ServiceSubscription.objects.create(
            user=self.fail_user,
            service=MemberService.objects.get(pk=settings.DEFAULT_ACCOUNT_SERVICE),
            state=ServiceSubscription.SUSPENDED,
        )
        # and a test card for fail case
        self.not_ok_card = NFCCard.objects.create(
            user=self.fail_user,
            cardid="TESTABC",
        )
        self.not_ok_card.save()

        self.fail_subscription.save()

    def test_list(self, mock):
        url = reverse("access-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_501_NOT_IMPLEMENTED)

    def test_access_phone_list_unauthenticated(self, mock):
        url = reverse("access-phone")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_access_phone_list_wrongauth(self, mock):
        url = reverse("access-phone")
        response = self.client.get(
            url, HTTP_AUTHORIZATION="Token {}".format("invalidtoken")
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_access_phone_list_authenticated(self, mock):
        url = reverse("access-phone")
        response = self.client.get(
            url, HTTP_AUTHORIZATION="Token {}".format(self.superuser_token)
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, self.ok_user.phone)
        self.assertContains(response, self.ok_user.email)
        self.assertNotContains(response, self.fail_user.phone)
        self.assertNotContains(response, self.fail_user.email)

    def test_access_phone_no_payload(self, mock):
        """
        Test with missing payload
        """
        url = reverse("access-phone")
        response = self.client.post(
            url, {"deviceid": self.device.deviceid, "payload": ""}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_access_phone_not_found(self, mock):
        """
        Test with not found number
        """
        url = reverse("access-phone")
        response = self.client.post(
            url, {"deviceid": self.device.deviceid, "payload": "+358111111111"}
        )
        self.assertEqual(response.status_code, 480)

    def test_access_phone_ok(self, mock):
        """
        Test with ok user and phone number
        """
        url = reverse("access-phone")
        response = self.client.post(
            url, {"deviceid": self.device.deviceid, "payload": self.ok_user.phone}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_access_phone_notok(self, mock):
        url = reverse("access-phone")
        # empty mail queue
        mail.outbox = []

        response = self.client.post(
            url, {"deviceid": self.device.deviceid, "payload": self.fail_user.phone}
        )

        # check that we notified the user by email of this failure
        self.assertIn("Hei", mail.outbox[0].body, "Hei")
        self.assertIn(
            "Käyttäjätililläsi ei ole tällähetkellä pääsyä oveen.",
            mail.outbox[0].body,
            "failure notification intro text",
        )
        # list of services in the mail
        self.assertIn(
            f"{self.fail_user.servicesubscription_set.first().service.name}: {self.fail_user.servicesubscription_set.first().state}",
            mail.outbox[0].body,
            "first ss state",
        )
        self.assertIn(settings.SITE_URL, mail.outbox[0].body, "siteurl")
        self.assertEqual(response.status_code, 481)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        EMAIL_HOST="example.com",
        EMAIL_TIMEOUT=1  # just to be fast in tests
    )
    def test_access_phone_notok_signal_fail(self, mock):
        """
        Test that signal does not fail even with broken smtp settings

        Django test cases normally run with memory backend for emails, but for
        this test it has been switched to smtp backend and given invalid settings
        so that it throws error
        """
        url = reverse("access-phone")
        # empty mail queue
        mail.outbox = []

        response = self.client.post(
            url, {"deviceid": self.device.deviceid, "payload": self.fail_user.phone}
        )

        # still getting a correct status (not 500)
        self.assertEqual(response.status_code, 481)

        # no email in outbox (just shows that we are not using the memory backend)
        self.assertEqual(len(mail.outbox), 0)

    def test_access_phone_empty(self, mock):
        url = reverse("access-phone")
        response = self.client.post(
            url, {"deviceid": self.device.deviceid, "payload": ""}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_device(self, mock):
        url = reverse("access-phone")
        response = self.client.post(
            url, {"deviceid": "not_a_valid_device", "payload": self.ok_user.phone}
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_nfc_ok(self, mock):
        url = reverse("access-nfc")
        response = self.client.post(
            url, {"deviceid": self.device.deviceid, "payload": self.ok_card.cardid}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_nfc_ok2(self, mock):
        url = reverse("access-nfc")
        response = self.client.post(
            url, {"deviceid": self.device.deviceid, "payload": self.ok_card2.cardid}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_nfc_notok(self, mock):
        url = reverse("access-nfc")
        response = self.client.post(
            url, {"deviceid": self.device.deviceid, "payload": self.not_ok_card.cardid}
        )
        self.assertEqual(response.status_code, 481)

    def test_nfc_empty(self, mock):
        url = reverse("access-nfc")
        response = self.client.post(
            url, {"deviceid": self.device.deviceid, "payload": ""}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_nfc_not_found(self, mock):
        url = reverse("access-nfc")
        response = self.client.post(
            url, {"deviceid": self.device.deviceid, "payload": "doesnotexists"}
        )
        self.assertEqual(response.status_code, 480)

    def test_access_mxid_no_payload(self, mock):
        """
        Test with missing payload
        """
        url = reverse("access-mxid")
        response = self.client.post(
            url, {"deviceid": self.device.deviceid, "payload": ""}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_access_mxid_not_found(self, mock):
        """
        Test with not found mxid
        """
        url = reverse("access-mxid")
        response = self.client.post(
            url, {"deviceid": self.device.deviceid, "payload": "@notexists:example.com"}
        )
        self.assertEqual(response.status_code, 480)

    def test_access_mxid_ok(self, mock):
        """
        Test with ok user and mxid
        """
        url = reverse("access-mxid")
        response = self.client.post(
            url, {"deviceid": self.device.deviceid, "payload": self.ok_user.mxid}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_access_mxid_notok(self, mock):
        url = reverse("access-mxid")
        response = self.client.post(
            url, {"deviceid": self.device.deviceid, "payload": self.fail_user.mxid}
        )
        self.assertEqual(response.status_code, 481)

    def test_unknown_mxid_device(self, mock):
        url = reverse("access-mxid")
        response = self.client.post(
            url, {"deviceid": "not_a_valid_device", "payload": self.ok_user.mxid}
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def tearDown(self):
        CustomUser.objects.all().delete()
        Token.objects.all().delete()
