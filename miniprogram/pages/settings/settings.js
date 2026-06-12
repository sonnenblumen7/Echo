var config = require('../../config')
var BASE_URL = config.BASE_URL

// 手机号脱敏：138****8000
function maskPhone(phone) {
  if (!phone || phone.length < 7) return phone
  return phone.substring(0, 3) + '****' + phone.substring(7)
}

function getOpenid() {
  return getApp().globalData.openid || wx.getStorageSync('openid') || ''
}

Page({
  data: {
    contacts: [],
    phone: '',
    name: '',
    email: ''
  },

  onShow: function () {
    this.loadContacts()
  },

  loadContacts: function () {
    var ctx = this
    wx.request({
      url: BASE_URL + '/contacts',
      method: 'GET',
      header: {
        'X-WX-OPENID': getOpenid()
      },
      success: function (r) {
        if (r.data && r.data.contacts) {
          // 对联系人手机号进行脱敏处理
          var contacts = r.data.contacts.map(function (c) {
            return Object.assign({}, c, {
              phone: maskPhone(c.phone),
              phone_raw: c.phone  // 保留原始号码用于删除等操作
            })
          })
          ctx.setData({ contacts: contacts })
          console.log('loadContacts: %d 条联系人', contacts.length)
        }
      },
      fail: function (err) {
        console.log('loadContacts 失败:', err)
      }
    })
  },

  onPhoneInput: function (e) {
    this.setData({ phone: e.detail.value })
  },

  onNameInput: function (e) {
    this.setData({ name: e.detail.value })
  },

  onEmailInput: function (e) {
    this.setData({ email: e.detail.value })
  },

  saveContact: function () {
    var ctx = this
    var phone = ctx.data.phone.trim()
    var name = ctx.data.name.trim()
    var email = ctx.data.email.trim()

    if (!phone && !email) {
      wx.showToast({ title: '请填写手机号或邮箱', icon: 'none' })
      return
    }

    if (phone && !/^1[3-9]\d{9}$/.test(phone)) {
      wx.showToast({ title: '手机号格式错误', icon: 'none' })
      return
    }

    if (email && !/^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(email)) {
      wx.showToast({ title: '邮箱格式错误', icon: 'none' })
      return
    }

    wx.request({
      url: BASE_URL + '/contacts',
      method: 'POST',
      header: {
        'Content-Type': 'application/json',
        'X-WX-OPENID': getOpenid()
      },
      data: { phone: phone, name: name || null, email: email },
      success: function (r) {
        if (r.statusCode === 409) {
          wx.showToast({ title: '该手机号或邮箱已存在', icon: 'none' })
          return
        }
        if (r.data && r.data.status === 'ok') {
          console.log('saveContact 成功:', r.data)
          wx.showToast({ title: '联系人已保存', icon: 'success' })
          ctx.setData({ phone: '', name: '', email: '' })
          ctx.loadContacts()
        }
      },
      fail: function (err) {
        console.log('saveContact 失败:', err)
        wx.showToast({ title: '保存失败', icon: 'error' })
      }
    })
  },

  deleteContact: function (e) {
    var ctx = this
    var id = e.currentTarget.dataset.id

    if (ctx.data.contacts.length <= 1 && wx.getStorageSync('protecting')) {
      wx.showModal({
        title: '无法删除',
        content: '守护中不能删除最后一位联系人，请先结束守护',
        showCancel: false
      })
      return
    }

    wx.showModal({
      title: '确认删除',
      content: '确定删除该联系人？',
      success: function (res) {
        if (!res.confirm) return

        wx.request({
          url: BASE_URL + '/contacts/' + id,
          method: 'DELETE',
          header: {
            'X-WX-OPENID': getOpenid()
          },
          success: function (r) {
            if (r.data && r.data.status === 'ok') {
              console.log('deleteContact 成功: id=%d', id)
              wx.showToast({ title: '已删除', icon: 'success' })
              ctx.loadContacts()
            }
          },
          fail: function (err) {
            console.log('deleteContact 失败:', err)
            wx.showToast({ title: '删除失败', icon: 'error' })
          }
        })
      }
    })
  }
})
