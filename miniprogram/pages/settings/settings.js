var config = require('../../config')
var BASE_URL = config.BASE_URL

Page({
  data: {
    contacts: [],
    phone: '',
    name: ''
  },

  onShow: function () {
    this.loadContacts()
  },

  loadContacts: function () {
    var ctx = this
    wx.request({
      url: BASE_URL + '/contacts',
      method: 'GET',
      success: function (r) {
        if (r.data && r.data.contacts) {
          ctx.setData({ contacts: r.data.contacts })
          console.log('loadContacts: %d 条联系人', r.data.contacts.length)
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

  saveContact: function () {
    var ctx = this
    var phone = ctx.data.phone.trim()
    var name = ctx.data.name.trim()

    if (!phone) {
      wx.showToast({ title: '请输入手机号', icon: 'none' })
      return
    }

    if (!/^1[3-9]\d{9}$/.test(phone)) {
      wx.showToast({ title: '手机号格式错误', icon: 'none' })
      return
    }

    wx.request({
      url: BASE_URL + '/contacts',
      method: 'POST',
      header: { 'Content-Type': 'application/json' },
      data: { phone: phone, name: name || null },
      success: function (r) {
        if (r.statusCode === 409) {
          wx.showToast({ title: '该手机号已存在', icon: 'none' })
          return
        }
        if (r.data && r.data.status === 'ok') {
          console.log('saveContact 成功:', r.data)
          wx.showToast({ title: '联系人已保存', icon: 'success' })
          ctx.setData({ phone: '', name: '' })
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
