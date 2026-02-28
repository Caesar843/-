from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from apps.store.models import Shop, ContractAttachment, ContractSignature
import datetime


class DTOForm(forms.Form):
    """
    [架构基类] DTO 构建专用表单

    设计意图：
    1. 明确该 Form 不具备持久化能力（无 save 方法）。
    2. 仅用于输入清洗与 UI 级校验。
    """
    pass


class ShopForm(DTOForm):
    """
    店铺创建表单

    [职责边界]
    - 输入：前端原始数据
    - 输出：清洗后的 name (str), area (Decimal)
    - 校验：格式校验、数值范围校验
    """
    name = forms.CharField(
        label=_("店铺名称"),
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '请输入店铺名称'})
    )
    area = forms.DecimalField(
        label=_("经营面积"),
        min_value=0.01,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '请输入经营面积 (㎡)'}),
        error_messages={'min_value': _("店铺面积必须大于 0")}
    )

    # 注意：此处无需 clean_name 查重，查重是 Service 的职责（可能涉及并发锁）


class ContractForm(DTOForm):
    """
    合同草拟表单

    [职责边界]
    - 输入：前端原始数据
    - 输出：shop_id (int), start_date (date), end_date (date)
    - 校验：日期顺序 (UI 逻辑)
    """
    # 使用 ModelChoiceField 仅为了利用 Django 的 Widget 生成下拉框
    # 但在 clean 阶段我们会剥离 ORM 对象
    shop = forms.ModelChoiceField(
        queryset=Shop.objects.filter(is_deleted=False),
        label=_("关联店铺"),
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label=_("请选择店铺")
    )
    current_year = datetime.datetime.now().year
    start_date = forms.DateField(
        label=_("开始日期"),
        widget=forms.SelectDateWidget(
            years=range(current_year, current_year + 10),
            attrs={'class': 'form-select'}
        )
    )
    end_date = forms.DateField(
        label=_("结束日期"),
        widget=forms.SelectDateWidget(
            years=range(current_year, current_year + 10),
            attrs={'class': 'form-select'}
        )
    )
    monthly_rent = forms.DecimalField(
        label=_("月租金"),
        min_value=0.01,
        max_digits=8,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '请输入月租金'})
    )
    deposit = forms.DecimalField(
        label=_("押金"),
        min_value=0,
        max_digits=8,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '请输入押金'}),
        initial=0
    )
    payment_cycle = forms.ChoiceField(
        label=_("缴费周期"),
        choices=[
            ('MONTHLY', _('月付')),
            ('QUARTERLY', _('季付')),
            ('SEMIANNUALLY', _('半年付')),
            ('ANNUALLY', _('年付'))
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        initial='MONTHLY'
    )

    def clean_shop(self) -> int:
        """
        [关键解耦]
        将 ORM 对象转换为纯 ID。
        View 层获取到的 cleaned_data['shop'] 将是 int，而非 Shop 实例。
        """
        shop_instance = self.cleaned_data['shop']
        return shop_instance.id

    def clean(self):
        """
        UI 级逻辑校验：结束日期必须晚于开始日期
        """
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date:
            if end_date <= start_date:
                raise ValidationError(_("合同结束日期必须晚于开始日期"))

        return cleaned_data


class ContractAttachmentUploadForm(DTOForm):
    attachment_type = forms.ChoiceField(
        label=_("附件类型"),
        choices=ContractAttachment.AttachmentType.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    file = forms.FileField(
        label=_("附件文件"),
        widget=forms.ClearableFileInput(attrs={"class": "form-control"}),
    )
    remark = forms.CharField(
        label=_("备注"),
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "可选备注"}),
    )

    def clean_file(self):
        uploaded_file = self.cleaned_data["file"]
        max_size = 20 * 1024 * 1024
        if uploaded_file.size > max_size:
            raise ValidationError(_("文件大小不能超过 20MB"))
        return uploaded_file


class ContractSignatureForm(DTOForm):
    party_type = forms.ChoiceField(
        label=_("签署方"),
        choices=ContractSignature.PartyType.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    signer_name = forms.CharField(
        label=_("签署人"),
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "请输入签署人姓名"}),
    )
    signer_title = forms.CharField(
        label=_("职务"),
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "可选"}),
    )
    sign_method = forms.ChoiceField(
        label=_("签署方式"),
        choices=ContractSignature.SignMethod.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    signed_at = forms.DateTimeField(
        label=_("签署时间"),
        input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"],
        widget=forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}),
    )
    attachment = forms.ModelChoiceField(
        label=_("关联附件"),
        queryset=ContractAttachment.objects.none(),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
        empty_label=_("不关联"),
    )
    evidence_hash = forms.CharField(
        label=_("证据哈希"),
        max_length=64,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "可选，64位哈希"}),
    )
    comment = forms.CharField(
        label=_("备注"),
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "可选备注"}),
    )

    def __init__(self, *args, contract=None, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = ContractAttachment.objects.none()
        if contract is not None:
            queryset = ContractAttachment.objects.filter(contract=contract).order_by("-created_at")
        self.fields["attachment"].queryset = queryset

    def clean_evidence_hash(self):
        evidence_hash = (self.cleaned_data.get("evidence_hash") or "").strip()
        if evidence_hash and len(evidence_hash) != 64:
            raise ValidationError(_("证据哈希长度必须为 64 位"))
        return evidence_hash
