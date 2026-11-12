const nodemailer = require('nodemailer');

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'Content-Type',
  'Access-Control-Allow-Methods': 'POST, OPTIONS'
};

function getEnvValue(...keys) {
  for (const key of keys) {
    const value = process.env[key];
    if (value !== undefined && value !== null && String(value).trim() !== '') {
      return String(value).trim();
    }
  }
  return '';
}

function normalizeSmtpCredential(value) {
  return String(value || '').replace(/\s+/g, '');
}

exports.handler = async function (event) {
  if (event.httpMethod === 'OPTIONS') {
    return {
      statusCode: 200,
      headers: corsHeaders,
      body: ''
    };
  }

  if (event.httpMethod !== 'POST') {
    return {
      statusCode: 405,
      headers: corsHeaders,
      body: JSON.stringify({ ok: false, error: 'Method not allowed' })
    };
  }

  try {
    const payload = JSON.parse(event.body || '{}');
    const toEmail = payload.to_email || getEnvValue('EMAIL_TO', 'TO_EMAIL');
    const subject = payload.subject || 'Alvin 的赎罪计划';
    const bodyText = payload.body || 'Alvin：已收到你的道歉与礼物。';
    const htmlText = payload.html || `<p>${bodyText.replace(/\n/g, '<br>')}</p>`;

    const smtpHost = getEnvValue('SMTP_HOST', 'HOST');
    const smtpUser = normalizeSmtpCredential(getEnvValue('SMTP_USER', 'USER', 'EMAIL_USER'));
    const smtpPass = normalizeSmtpCredential(getEnvValue('SMTP_PASS', 'PASS', 'EMAIL_PASS', 'PASSWORD'));
    const smtpFrom = normalizeSmtpCredential(getEnvValue('SMTP_FROM', 'FROM', 'EMAIL_FROM') || smtpUser);
    const smtpPort = Number(getEnvValue('SMTP_PORT', 'PORT') || '587');
    const useSsl = String(getEnvValue('SMTP_USE_SSL', 'USE_SSL', 'SSL') || 'false').toLowerCase() === 'true';

    if (!smtpHost || !smtpUser || !smtpPass || !smtpFrom || !toEmail) {
      return {
        statusCode: 500,
        headers: corsHeaders,
        body: JSON.stringify({
          ok: false,
          error: 'SMTP is not configured in Netlify environment variables. Required: SMTP_HOST/SMTP_USER/SMTP_PASS/SMTP_FROM/EMAIL_TO (or legacy aliases HOST/USER/PASS/FROM/EMAIL_TO).'
        })
      };
    }

    const transporter = nodemailer.createTransport({
      host: smtpHost,
      port: smtpPort,
      secure: useSsl,
      auth: {
        user: smtpUser,
        pass: smtpPass
      },
      tls: {
        rejectUnauthorized: false
      }
    });

    await transporter.sendMail({
      from: smtpFrom,
      to: toEmail,
      subject,
      text: bodyText,
      html: htmlText
    });

    return {
      statusCode: 200,
      headers: {
        ...corsHeaders,
        'Content-Type': 'application/json; charset=utf-8'
      },
      body: JSON.stringify({ ok: true, message: `Email sent to ${toEmail}` })
    };
  } catch (error) {
    return {
      statusCode: 500,
      headers: {
        ...corsHeaders,
        'Content-Type': 'application/json; charset=utf-8'
      },
      body: JSON.stringify({
        ok: false,
        error: error && error.message ? error.message : 'Email send failed'
      })
    };
  }
};
