const nodemailer = require('nodemailer');

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'Content-Type',
  'Access-Control-Allow-Methods': 'POST, OPTIONS'
};

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
    const toEmail = payload.to_email || process.env.EMAIL_TO || '';
    const subject = payload.subject || 'Alvin 的赎罪计划';
    const bodyText = payload.body || 'Alvin：已收到你的道歉与礼物。';
    const htmlText = payload.html || `<p>${bodyText.replace(/\n/g, '<br>')}</p>`;

    const smtpHost = process.env.SMTP_HOST;
    const smtpUser = process.env.SMTP_USER;
    const smtpPass = process.env.SMTP_PASS;
    const smtpFrom = process.env.SMTP_FROM || smtpUser;
    const smtpPort = Number(process.env.SMTP_PORT || 587);
    const useSsl = String(process.env.SMTP_USE_SSL || 'false').toLowerCase() === 'true';

    if (!smtpHost || !smtpUser || !smtpPass || !smtpFrom || !toEmail) {
      return {
        statusCode: 500,
        headers: corsHeaders,
        body: JSON.stringify({
          ok: false,
          error: 'SMTP is not configured in Netlify environment variables.'
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
