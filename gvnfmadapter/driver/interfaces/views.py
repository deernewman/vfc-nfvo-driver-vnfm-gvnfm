# Copyright 2017 ZTE Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import inspect
import json
import logging
import time

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from driver.pub.utils import restcall
from driver.pub.utils.restcall import req_by_msb

logger = logging.getLogger(__name__)


@api_view(http_method_names=['POST'])
def instantiate_vnf(request, *args, **kwargs):
    try:
        input_data = {}
        input_data["vnfdId"] = ignorcase_get(request.data, "vnfDescriptorId")
        input_data["vnfInstanceName"] = ignorcase_get(request.data, "vnfInstanceName")
        input_data["vnfInstanceDescription"] = ignorcase_get(request.data, "vnfInstanceDescription")
        vnfm_id = ignorcase_get(kwargs, "vnfmid")
        ret, resp = do_createvnf(request, input_data, vnfm_id)
        if ret != 0:
            return resp
        logger.info("[%s]resp_data=%s", fun_name(), resp)
        vnfInstanceId = resp["vnfInstanceId"]
        logger.info("[%s]vnfInstanceId=%s", fun_name(), vnfInstanceId)
        input_data = {}
        input_data["flavourId"] = ignorcase_get(request.data, "flavourId")
        input_data["extVirtualLinks"] = ignorcase_get(request.data, "extVirtualLink")
        input_data["additionalParams"] = ignorcase_get(request.data, "additionalParams")
        input_data["flavourId"] = ignorcase_get(request.data, "flavourId")
        ret, resp = do_instvnf(vnfInstanceId, request, input_data, vnfm_id)
        if ret != 0:
            return resp
        resp_data = {"jobId":"", "vnfInstanceId":""}
        resp_data["vnfInstanceId"] = vnfInstanceId
        resp_data["jobId"] = resp["vnfLcOpId"]
    except Exception as e:
        logger.error("Error occurred when instantiating VNF")
        raise e
    return Response(data=resp_data, status=status.HTTP_201_CREATED)


@api_view(http_method_names=['POST'])
def terminate_vnf(request, *args, **kwargs):
    vnfm_id = ignorcase_get(kwargs, "vnfmid")
    vnfInstanceId = ignorcase_get(kwargs, "vnfInstanceId")
    try:
        input_data = {}
        input_data["terminationType"] = ignorcase_get(request.data, "terminationType")
        input_data["gracefulTerminationTimeout"] = ignorcase_get(request.data, "gracefulTerminationTimeout")
        ret, resp = do_terminatevnf(request, input_data, vnfm_id, vnfInstanceId)
        if ret != 0:
            return resp
        jobId = ignorcase_get(resp, "vnfLcOpId")
        gracefulTerminationTimeout = ignorcase_get(request.data, "gracefulTerminationTimeout")
        ret, response = wait4job(vnfm_id,jobId,gracefulTerminationTimeout)
        if ret != 0:
            return response
        ret, resp = do_deletevnf(request, vnfm_id, vnfInstanceId)
        if ret != 0:
            return resp
    except Exception as e:
        logger.error("Error occurred when terminating VNF")
        raise e
    return Response(data=resp, status=status.HTTP_204_NO_CONTENT)


@api_view(http_method_names=['GET'])
def query_vnf(request, *args, **kwargs):
    vnfm_id = ignorcase_get(kwargs, "vnfmid")
    vnfInstanceId = ignorcase_get(kwargs, "vnfInstanceId")
    try:
        logger.debug("[%s] request.data=%s", fun_name(), request.data)
        ret, resp = do_queryvnf(request, vnfm_id, vnfInstanceId)
        if ret != 0:
            return resp
        query_vnf_resp_mapping = {
            "vnfInstanceId": "",
            "vnfInstanceName": "",
            "vnfInstanceDescription": "",
            "vnfdId": "",
            "vnfPackageId": "",
            "version": "",
            "vnfProvider": "",
            "vnfType": "",
            "vnfStatus": ""
        }
        resp_response_data = mapping_conv(query_vnf_resp_mapping, ignorcase_get(resp, "ResponseInfo"))
        resp_data = {
            "vnfInfo":resp_response_data
        }
        resp_data["vnfInfo"]["version"] = ignorcase_get(ignorcase_get(resp, "ResponseInfo"), "vnfSoftwareVersion")
        if ignorcase_get(ignorcase_get(resp, "ResponseInfo"), "instantiationState"):
            if ignorcase_get(ignorcase_get(resp, "ResponseInfo"), "instantiationState") == "INSTANTIATED":
                resp_data["vnfInfo"]["vnfStatus"] = "ACTIVE"
        if ignorcase_get(ignorcase_get(resp, "ResponseInfo"), "vnfInstanceId"):
            resp_data["vnfInfo"]["vnfInstanceId"] = ignorcase_get(ignorcase_get(resp, "ResponseInfo"), "vnfInstanceId")
        logger.debug("[%s]resp_data=%s", fun_name(), resp_data)
    except Exception as e:
        logger.error("Error occurred when querying VNF information.")
        raise e
    return Response(data=resp_data, status=status.HTTP_200_OK)


@api_view(http_method_names=['GET'])
def operation_status(request, *args, **kwargs):
    data = {}
    try:
        logger.debug("[%s] request.data=%s", fun_name(), request.data)
        vnfm_id = ignorcase_get(kwargs, "vnfmid")
        jobId = ignorcase_get(kwargs, "jobId")
        responseId = ignorcase_get(kwargs, "responseId")
        ret, vnfm_info = get_vnfminfo_from_nslcm(vnfm_id)
        if ret != 0:
            return Response(data={'error': ret[1]}, status=ret[2])
        logger.debug("[%s] vnfm_info=%s", fun_name(), vnfm_info)
        ret = call_vnfm("api/vnflcm/v1/vnf_lc_ops/%s?responseId=%s" % (jobId, responseId), "GET", vnfm_info)
        if ret[0] != 0:
            return Response(data={'error': ret[1]}, status=ret[2])
        resp_data = json.JSONDecoder().decode(ret[1])
        logger.info("[%s]resp_data=%s", fun_name(), resp_data)
        ResponseInfo = ignorcase_get(resp_data, "ResponseInfo")
        operation_data = {}
        operation_data["jobId"] = ignorcase_get(ResponseInfo, "vnfLcOpId")
        operation_data["responseDescriptor"] = {}
        operation_data["responseDescriptor"]["status"] = ignorcase_get(ignorcase_get(ResponseInfo, "responseDescriptor"),"lcmOperationStatus")
        operation_data["responseDescriptor"]["progress"] = ignorcase_get(ignorcase_get(ResponseInfo, "responseDescriptor"),"progress")
        operation_data["responseDescriptor"]["statusDescription"] = ignorcase_get(ignorcase_get(ResponseInfo, "responseDescriptor"),"statusDescription")
        operation_data["responseDescriptor"]["errorCode"] = ignorcase_get(ignorcase_get(ResponseInfo, "responseDescriptor"),"errorCode")
        operation_data["responseDescriptor"]["responseId"] = ignorcase_get(ignorcase_get(ResponseInfo, "responseDescriptor"),"responseId")
        operation_data["responseDescriptor"]["responseHistoryList"] = ignorcase_get(ignorcase_get(ResponseInfo, "responseDescriptor"),"responseHistoryList")
    except Exception as e:
        logger.error("Error occurred when getting operation status information.")
        raise e
    return Response(data=operation_data, status=status.HTTP_200_OK)


@api_view(http_method_names=['PUT'])
def grantvnf(request, *args, **kwargs):
    logger.info("=====grantvnf=====")
    try:
        resp_data = {}
        logger.info("req_data = %s", request.data)
        ret = req_by_msb('api/nslcm/v1/grantvnf', "POST", content=json.JSONEncoder().encode(request.data))
        logger.info("ret = %s", ret)
        if ret[0] != 0:
            return Response(data={'error': ret[1]}, status=ret[2])
        resp = json.JSONDecoder().decode(ret[1])
        resp_data['vimid'] = ignorcase_get(resp['vim'], 'vimid')
        resp_data['tenant'] = ignorcase_get(ignorcase_get(resp['vim'], 'accessinfo'), 'tenant')
        logger.info("[%s]resp_data=%s", fun_name(), resp_data)
    except Exception as e:
        logger.error("Error occurred in Grant VNF.")
        raise e
    return Response(data=resp_data, status=ret[2])


@api_view(http_method_names=['POST'])
def notify(request, *args, **kwargs):
    try:
        logger.info("[%s]req_data = %s", fun_name(), request.data)
        vnfinstanceid = ignorcase_get(request.data, 'vnfinstanceid')
        ret = req_by_msb("api/nslcm/v1/vnfs/%s/Notify" % vnfinstanceid, "POST", json.JSONEncoder().encode(request.data))
        logger.info("[%s]data = %s", fun_name(), ret)
        if ret[0] != 0:
            return Response(data={'error': ret[1]}, status=ret[2])
    except Exception as e:
        logger.error("Error occurred in LCM notification.")
        raise e
    return Response(data=None, status=ret[2])


@api_view(http_method_names=['GET'])
def get_vnfpkgs(request, *args, **kwargs):
    logger.info("Enter %s", fun_name())
    ret = req_by_msb("api/nslcm/v1/vnfpackage", "GET")
    if ret[0] != 0:
        return Response(data={'error': ret[1]}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    resp = json.JSONDecoder().decode(ret[1])
    return Response(data=resp, status=status.HTTP_200_OK)


def call_vnfm(resource, method, vnfm_info, data=""):
    ret = restcall.call_req(
        base_url=ignorcase_get(vnfm_info, "url"),
        user=ignorcase_get(vnfm_info, "userName"),
        passwd=ignorcase_get(vnfm_info, "password"),
        auth_type=restcall.rest_no_auth,
        resource=resource,
        method=method,
        content=json.JSONEncoder().encode(data))
    return ret


def mapping_conv(keyword_map, rest_return):
    resp_data = {}
    for param in keyword_map:
        if keyword_map[param]:
            if isinstance(keyword_map[param], dict):
                resp_data[param] = mapping_conv(keyword_map[param], ignorcase_get(rest_return, param))
            else:
                resp_data[param] = ignorcase_get(rest_return, param)
    return resp_data

def fun_name():
    return "=================%s==================" % inspect.stack()[1][3]


def ignorcase_get(args, key):
    if not key:
        return ""
    if not args:
        return ""
    if key in args:
        return args[key]
    for old_key in args:
        if old_key.upper() == key.upper():
            return args[old_key]
    return ""


def get_vnfminfo_from_nslcm(vnfm_id):
    ret = req_by_msb("api/aai-esr-server/v1/vnfms/%s" % vnfm_id, "GET")
    if ret[0] != 0:
        return 255, Response(data={'error': ret[1]}, status=ret[2])
    vnfm_info = json.JSONDecoder().decode(ret[1])
    logger.debug("[%s] vnfm_info=%s", fun_name(), vnfm_info)
    return 0, vnfm_info


def wait4job(vnfm_id,jobId,gracefulTerminationTimeout):
    begin_time = time.time()
    try:
        ret, vnfm_info = get_vnfminfo_from_nslcm(vnfm_id)
        if ret != 0:
            return 255, Response(data={"error":"Fail to get VNFM!"}, status=status.HTTP_412_PRECONDITION_FAILED)

        responseId = None
        while ret == 0:
            cur_time = time.time()
            if gracefulTerminationTimeout and (cur_time - begin_time > gracefulTerminationTimeout):
                return 255, Response(data={"error":"Fail to terminate VNF!"}, status=status.HTTP_408_REQUEST_TIMEOUT)
            ret = call_vnfm("api/vnflcm/v1/vnf_lc_ops/%s?responseId=%s" % (jobId, responseId), "GET", vnfm_info)
            if ret[0] != 0:
                return 255, Response(data={"error":"Fail to get job status!"}, status=status.HTTP_412_PRECONDITION_FAILED)
            if json.JSONDecoder().decode(ret[2]) != 200:
                return 255, Response(data={"error":"Fail to get job status!"}, status=status.HTTP_412_PRECONDITION_FAILED)
            job_info = json.JSONDecoder().decode(ret[1])
            responseId = ignorcase_get(ignorcase_get(job_info, "VnfLcOpResponseDescriptor"), "responseId")
            progress = ignorcase_get(ignorcase_get(job_info, "VnfLcOpResponseDescriptor"), "progress")
            if progress == "100":
                return 0, Response(data={"success":"success"}, status=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        logger.error("Error occurred when do_createvnf")
        return 255, Response(data={"error":"Exception caught! Fail to get job status!"}, status=status.HTTP_412_PRECONDITION_FAILED)


def do_createvnf(request, data, vnfm_id):
    logger.debug("[%s] request.data=%s", fun_name(), request.data)
    try:
        ret, vnfm_info = get_vnfminfo_from_nslcm(vnfm_id)
        if ret != 0:
            return ret, vnfm_info
        ret = call_vnfm("api/vnflcm/v1/vnf_instances", "POST", vnfm_info, data)
        logger.debug("[%s] call_req ret=%s", fun_name(), ret)
        if ret[0] != 0:
            return 255, Response(data={'error': ret[1]}, status=ret[2])
        resp = json.JSONDecoder().decode(ret[1])
    except Exception as e:
        logger.error("Error occurred when do_createvnf")
        raise e
    return 0, resp


def do_instvnf(vnfInstanceId, request, data, vnfm_id):
    logger.debug("[%s] request.data=%s", fun_name(), request.data)
    try:
        ret, vnfm_info = get_vnfminfo_from_nslcm(vnfm_id)
        if ret != 0:
            return ret, vnfm_info
        ret = call_vnfm("api/vnflcm/v1/vnf_instances/%s/instantiate" % vnfInstanceId, "POST", vnfm_info, data)
        logger.debug("[%s] call_req ret=%s", fun_name(), ret)
        if ret[0] != 0:
            return 255, Response(data={'error': ret[1]}, status=ret[2])
        resp = json.JSONDecoder().decode(ret[1])
    except Exception as e:
        logger.error("Error occurred when do_instvnf")
        raise e
    return 0, resp


def do_terminatevnf(request, data, vnfm_id, vnfInstanceId):
    logger.debug("[%s] request.data=%s", fun_name(), request.data)
    try:
        ret, vnfm_info = get_vnfminfo_from_nslcm(vnfm_id)
        if ret != 0:
            return ret,vnfm_info
        ret = call_vnfm("api/vnflcm/v1/vnf_instances/%s/terminate"% vnfInstanceId,"POST", vnfm_info, data)
        if ret[0] != 0:
            return 255, Response(data={'error': ret[1]}, status=ret[2])
        resp_data = json.JSONDecoder().decode(ret[1])
        logger.debug("[%s]resp_data=%s", fun_name(), resp_data)
    except Exception as e:
        logger.error("Error occurred when do_terminatevnf")
        raise e
    return 0, resp_data


def do_deletevnf(request, vnfm_id, vnfInstanceId):
    logger.debug("[%s] request.data=%s", fun_name(), request.data)
    try:
        ret, vnfm_info = get_vnfminfo_from_nslcm(vnfm_id)
        if ret != 0:
            return ret, vnfm_info
        ret = call_vnfm("api/vnflcm/v1/vnf_instances/%s" % vnfInstanceId, "DELETE", vnfm_info)
        if ret[0] != 0:
            return 255, Response(data={'error': ret[1]}, status=ret[2])
        resp_data = json.JSONDecoder().decode(ret[1])
        logger.debug("[%s]resp_data=%s", fun_name(), resp_data)
    except Exception as e:
        logger.error("Error occurred when do_deletevnf")
        raise e
    return 0, resp_data


def do_queryvnf(request, vnfm_id, vnfInstanceId):
    logger.debug("[%s] request.data=%s", fun_name(), request.data)
    try:
        ret, vnfm_info = get_vnfminfo_from_nslcm(vnfm_id)
        if ret != 0:
            return ret, vnfm_info
        ret = call_vnfm("api/vnflcm/v1/vnf_instances/%s" % vnfInstanceId, "GET", vnfm_info)
        if ret[0] != 0:
            return 255, Response(data={'error': ret[1]}, status=ret[2])
        resp_data = json.JSONDecoder().decode(ret[1])
        logger.debug("[%s]resp_data=%s", fun_name(), resp_data)
    except Exception as e:
        logger.error("Error occurred when do_query vnf")
        raise e
    return 0, resp_data
