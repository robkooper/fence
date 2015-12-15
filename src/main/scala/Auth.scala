import java.util.UUID

import Proxy._
import com.twitter.finagle.http._
import com.twitter.finagle.{SimpleFilter, http, Service}
import com.twitter.io.Buf
import com.twitter.server.util.JsonConverter
import com.twitter.util.{Base64StringEncoder, Future}

/**
  * Authentication and authorization methods.
  */
object Auth {

  val accessTokenStats = statsReceiver.counter("animal-kingdom-new-access-token")

  val checkTokenStats = statsReceiver.counter("animal-kingdom-check-access-token")

  def newAccessToken(key: UUID) = new Service[http.Request, http.Response] {
    def apply(req: http.Request): Future[http.Response] = {
      val token = Redis.newToken(key)
      val res = Response(req.version, Status.Ok)
      res.contentType = "application/json;charset=UTF-8"
      res.content = Buf.Utf8(JsonConverter.writeToString(Map("token"->token)))
      accessTokenStats.incr()
      Future.value(res)
    }
  }

  def checkToken(token: UUID) = new Service[http.Request, http.Response] {
    def apply(req: http.Request): Future[http.Response] = {
      val res = Response(req.version, Status.Ok)
      res.contentType = "application/json;charset=UTF-8"
      Redis.checkToken(token) match {
        case Some(ttl) => res.content = Buf.Utf8(JsonConverter.writeToString(Map("found"->"true","ttl"->ttl)))
        case None => res.content = Buf.Utf8(JsonConverter.writeToString(Map("found"->"false")))
      }
      checkTokenStats.incr()
      Future.value(res)
    }
  }

  def checkUsernamePassword(username: String, password: String): Boolean = {
    // FIXME: Look it up
    username == "open" && password == "sesame"
  }

  class AuthorizeToken extends SimpleFilter[Request, Response] {
    def apply(request: Request, continue: Service[Request, Response]) = {
      // validate token
      val active: Option[Boolean] = for {
        token <- request.headerMap.get(Fields.Authorization)
        ttl <- Redis.checkToken(UUID.fromString(token))
        if ttl > 0
      } yield true
      // forward if valid
      if (active.getOrElse(false)) {
        continue(request)
      } else {
        //        Future.exception(new IllegalArgumentException("You don't know the secret"))
        val errorResponse = Response(Version.Http11, Status.Forbidden)
        errorResponse.contentString = "Invalid token"
        Future(errorResponse)
      }
    }
  }

  class AuthorizeUserPassword extends SimpleFilter[Request, Response] {
    def apply(request: Request, continue: Service[Request, Response]) = {
      // validate credentials
      request.headerMap.get(Fields.Authorization) match {
        case Some(header) =>
          val credentials = new String(Base64StringEncoder.decode(header.substring(6))).split(":")
          if (credentials.size == 2 && checkUsernamePassword(credentials(0), credentials(1))) {
            continue(request)
          } else {
            val errorResponse = Response(Version.Http11, Status.Forbidden)
            errorResponse.contentString = "Invalid credentials"
            Future(errorResponse)
          }
        case None =>
          val errorResponse = Response(Version.Http11, Status.Forbidden)
          errorResponse.contentString = "Invalid credentials"
          Future(errorResponse)
      }
    }
  }
}