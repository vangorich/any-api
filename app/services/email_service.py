import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from app.core.config import settings

class EmailService:
    """邮件发送服务"""
    
    def __init__(self):
        """初始化SMTP配置"""
        self.smtp_host: Optional[str] = None
        self.smtp_port: int = 587
        self.smtp_user: Optional[str] = None
        self.smtp_password: Optional[str] = None
        self.smtp_from: Optional[str] = None
        self.smtp_use_tls: bool = True
        
    async def configure(self, config):
        """从系统配置更新SMTP设置"""
        self.smtp_host = config.smtp_host
        self.smtp_port = config.smtp_port or 587
        self.smtp_user = config.smtp_user
        self.smtp_password = config.smtp_password
        self.smtp_from = config.smtp_from or config.smtp_user
        self.smtp_use_tls = config.smtp_use_tls if hasattr(config, 'smtp_use_tls') else True
        
    def is_configured(self) -> bool:
        """检查SMTP是否已配置"""
        return all([
            self.smtp_host,
            self.smtp_user,
            self.smtp_password,
        ])
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """
        发送邮件
        
        Args:
            to_email: 收件人邮箱
            subject: 邮件主题
            html_content: HTML内容
            text_content: 纯文本内容（可选）
            
        Returns:
            发送是否成功
        """
        if not self.is_configured():
            raise Exception("SMTP not configured")
        
        try:
            # 创建邮件
            message = MIMEMultipart('alternative')
            message['Subject'] = subject
            message['From'] = self.smtp_from
            message['To'] = to_email
            
            # 添加纯文本部分
            if text_content:
                part1 = MIMEText(text_content, 'plain', 'utf-8')
                message.attach(part1)
            
            # 添加HTML部分
            part2 = MIMEText(html_content, 'html', 'utf-8')
            message.attach(part2)
            
            # 发送邮件
            # 端口465使用直接SSL连接，端口587手动控制STARTTLS
            if self.smtp_port == 465:
                # 端口465：直接使用SSL/TLS连接
                async with aiosmtplib.SMTP(
                    hostname=self.smtp_host,
                    port=self.smtp_port,
                    use_tls=True
                ) as smtp:
                    await smtp.login(self.smtp_user, self.smtp_password)
                    await smtp.send_message(message)
            else:
                # 端口587：手动控制STARTTLS流程
                # 1. 先建立明文连接（不自动升级）
                # 2. 手动调用starttls()
                # 3. 然后登录
                smtp = aiosmtplib.SMTP(
                    hostname=self.smtp_host,
                    port=self.smtp_port,
                    start_tls=False  # 禁用自动STARTTLS
                )
                connected = False
                try:
                    await smtp.connect()
                    connected = True
                    
                    if self.smtp_use_tls:
                        await smtp.starttls()
                    
                    await smtp.login(self.smtp_user, self.smtp_password)
                    await smtp.send_message(message)
                except Exception as e:
                    raise
                finally:
                    if connected:
                        try:
                            await smtp.quit()
                        except Exception:
                            pass
            
            return True
        except Exception as e:
            print(f"Email send error: {e}")
            return False
    
    async def send_verification_email(
        self,
        to_email: str,
        code: str,
        site_name: str = "Any API",
        username: Optional[str] = None
    ) -> bool:
        """
        发送验证码邮件
        
        Args:
            to_email: 收件人邮箱
            code: 验证码
            site_name: 网站名称
            username: 用户名（可选）
            
        Returns:
            发送是否成功
        """
        subject = f"{site_name} - 邮箱验证码"
        greeting = f"您好, {username}" if username else "您好"
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji";
                    background-color: #f4f4f7;
                    margin: 0;
                    padding: 0;
                }}
                .container {{
                    max-width: 600px;
                    margin: 40px auto;
                    padding: 20px;
                }}
                .card {{
                    background-color: #ffffff;
                    border-radius: 12px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
                    padding: 40px;
                }}
                h1 {{
                    font-size: 24px;
                    color: #333;
                    margin-top: 0;
                    text-align: center;
                }}
                 h2 {{
                    font-size: 18px;
                    color: #555;
                    font-weight: normal;
                    margin-bottom: 25px;
                    text-align: center;
                }}
                p {{
                    color: #555555;
                    line-height: 1.7;
                    font-size: 16px;
                }}
                .code-container {{
                    background-color: #f8f9fa;
                    border-radius: 8px;
                    padding: 20px;
                    text-align: center;
                    margin: 30px 0;
                }}
                .code {{
                    font-size: 36px;
                    font-weight: bold;
                    color: #3b82f6; /* A nice blue color */
                    letter-spacing: 8px;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 20px;
                    color: #999999;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="card">
                    <h1>{site_name}</h1>
                    <h2>邮箱安全验证</h2>
                    <p>{greeting}</p>
                    <p>您正在进行邮箱验证，您的验证码是：</p>
                    <div class="code-container">
                        <span class="code">{code}</span>
                    </div>
                    <p>验证码有效期为 <strong>10分钟</strong>，请尽快完成验证。</p>
                    <p>如果这不是您的操作，请忽略此邮件。</p>
                </div>
                <div class="footer">
                    <p>此邮件由系统自动发送，请勿回复</p>
                    <p>&copy; {site_name}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        {site_name} - 邮箱验证
        
        您好，
        
        您正在进行邮箱验证，您的验证码是：{code}
        
        验证码有效期为 10分钟，请尽快完成验证。
        
        如果这不是您的操作，请忽略此邮件。
        
        ---
        此邮件由系统自动发送，请勿回复
        © {site_name}
        """
        
        return await self.send_email(to_email, subject, html_content, text_content)
    
    async def send_password_reset_email(
        self,
        to_email: str,
        code: str,
        site_name: str = "Any API",
        username: Optional[str] = None
    ) -> bool:
        """
        发送密码重置邮件
        
        Args:
            to_email: 收件人邮箱
            code: 验证码
            site_name: 网站名称
            username: 用户名 (可选)
            
        Returns:
            发送是否成功
        """
        subject = f"{site_name} - 密码重置验证码"
        greeting = f"您好, {username}" if username else "您好"
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji";
                    background-color: #f4f4f7;
                    margin: 0;
                    padding: 0;
                }}
                .container {{
                    max-width: 600px;
                    margin: 40px auto;
                    padding: 20px;
                }}
                .card {{
                    background-color: #ffffff;
                    border-radius: 12px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
                    padding: 40px;
                }}
                 h1 {{
                    font-size: 24px;
                    color: #333;
                    margin-top: 0;
                    text-align: center;
                }}
                 h2 {{
                    font-size: 18px;
                    color: #555;
                    font-weight: normal;
                    margin-bottom: 25px;
                    text-align: center;
                }}
                p {{
                    color: #555555;
                    line-height: 1.7;
                    font-size: 16px;
                }}
                .code-container {{
                    background-color: #f8f9fa;
                    border-radius: 8px;
                    padding: 20px;
                    text-align: center;
                    margin: 30px 0;
                }}
                .code {{
                    font-size: 36px;
                    font-weight: bold;
                    color: #d946ef; /* A nice violet color for password reset */
                    letter-spacing: 8px;
                }}
                .warning {{
                    background-color: #fffbeb;
                    border-left: 4px solid #fbbd23;
                    padding: 15px;
                    margin-top: 20px;
                    font-size: 14px;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 20px;
                    color: #999999;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="card">
                    <h1>{site_name}</h1>
                    <h2>账户密码重置</h2>
                    <p>{greeting}</p>
                    <p>您正在重置账户密码，您的验证码是：</p>
                    <div class="code-container">
                        <span class="code">{code}</span>
                    </div>
                    <p>验证码有效期为 <strong>10分钟</strong>。</p>
                    <div class="warning">
                        <strong>安全提示：</strong>如果这不是您的操作，请立即修改您的账户密码并警惕账户安全风险。
                    </div>
                </div>
                <div class="footer">
                    <p>此邮件由系统自动发送，请勿回复</p>
                    <p>&copy; {site_name}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        {site_name} - 密码重置
        
        您好，
        
        您正在重置账户密码，您的验证码是：{code}
        
        ⚠️ 安全提示
        验证码有效期为 10分钟。
        如果这不是您的操作，请立即修改密码并联系管理员。
        
        ---
        此邮件由系统自动发送，请勿回复
        © {site_name}
        """
        
        return await self.send_email(to_email, subject, html_content, text_content)

# 全局邮件服务实例
email_service = EmailService()
