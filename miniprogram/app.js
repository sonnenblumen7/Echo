var config = require('./config')
var BASE_URL = config.BASE_URL

App({
  globalData: {
    openid: ''  // 用户唯一标识
  },

  onLaunch: function () {
    console.log("Echo App 启动")
    this.login()
  },

  login: function () {
    var app = this
    // 检查本地缓存的 openid
    var openid = wx.getStorageSync('openid')
    if (openid) {
      app.globalData.openid = openid
      console.log('使用缓存的 openid:', openid.substring(0, 8) + '****')
      return
    }

    // 没有缓存，调用微信登录
    wx.login({
      success: function (res) {
        if (!res.code) {
          console.error('wx.login 失败:', res)
          return
        }

        console.log('wx.login code:', res.code)

        // 发送 code 到后端换取 openid
        wx.request({
          url: BASE_URL + '/auth/login',
          method: 'POST',
          header: { 'Content-Type': 'application/json' },
          data: { code: res.code },
          success: function (r) {
            if (r.data && r.data.status === 'ok' && r.data.openid) {
              app.globalData.openid = r.data.openid
              wx.setStorageSync('openid', r.data.openid)
              console.log('登录成功，openid:', r.data.openid.substring(0, 8) + '****')
            } else {
              console.error('登录失败:', r.data)
            }
          },
          fail: function (err) {
            console.error('登录请求失败:', err)
          }
        })
      },
      fail: function (err) {
        console.error('wx.login 调用失败:', err)
      }
    })
  }
})
